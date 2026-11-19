import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const dbPath = process.env.DB_PATH ?? path.join(process.cwd(), "instance", "database.db");
fs.mkdirSync(path.dirname(dbPath), { recursive: true });

export const db = new Database(dbPath);
db.pragma("journal_mode = WAL");
db.exec(`
CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email VARCHAR(150) UNIQUE,
  password VARCHAR(150),
  first_name VARCHAR(150)
);
CREATE TABLE IF NOT EXISTS note (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data VARCHAR(10000),
  date DATETIME DEFAULT CURRENT_TIMESTAMP,
  user_id INTEGER REFERENCES user(id)
);`);

export type User = { id: number; email: string; password: string; first_name: string };
export type Note = { id: number; data: string; user_id: number };

export const findUserByEmail = (email: string | undefined) =>
  db.prepare("SELECT * FROM user WHERE email = ?").get(email ?? null) as User | undefined;
export const findUserById = (id: number) =>
  db.prepare("SELECT * FROM user WHERE id = ?").get(id) as User | undefined;
export const createUser = (email: string, firstName: string, password: string) =>
  Number(db.prepare("INSERT INTO user (email, password, first_name) VALUES (?, ?, ?)").run(email, password, firstName).lastInsertRowid);
export const notesFor = (userId: number) =>
  db.prepare("SELECT id, data FROM note WHERE user_id = ? ORDER BY id").all(userId) as Pick<Note, "id" | "data">[];
export const addNote = (data: string, userId: number) =>
  db.prepare("INSERT INTO note (data, user_id) VALUES (?, ?)").run(data, userId);
export const findNote = (id: unknown) =>
  db.prepare("SELECT * FROM note WHERE id = ?").get(id as number) as Note | undefined;
export const deleteNoteById = (id: number) => db.prepare("DELETE FROM note WHERE id = ?").run(id);

export function hashPassword(pw: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  return `scrypt$${salt}$${crypto.scryptSync(pw, salt, 64).toString("hex")}`;
}
export function checkPassword(stored: string, pw: string): boolean {
  const [alg, salt, hash] = stored.split("$");
  if (alg !== "scrypt" || !salt || !hash) return false;
  const a = Buffer.from(hash, "hex");
  const b = crypto.scryptSync(pw, salt, 64);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
