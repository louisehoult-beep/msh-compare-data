import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export function openDb(path = process.env.DB_PATH || 'data/app.db') {
  if (path !== ':memory:') mkdirSync(dirname(path), { recursive: true });
  const db = new DatabaseSync(path);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS members (
      id INTEGER PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      nmc_pin TEXT NOT NULL,
      role_category TEXT NOT NULL,
      employer_type TEXT NOT NULL,
      speciality TEXT NOT NULL DEFAULT '',
      region TEXT NOT NULL DEFAULT '',
      directory_visible INTEGER NOT NULL DEFAULT 0,
      mentoring TEXT NOT NULL DEFAULT 'none',
      email_notifications INTEGER NOT NULL DEFAULT 1,
      status TEXT NOT NULL DEFAULT 'pending',
      is_admin INTEGER NOT NULL DEFAULT 0,
      verified_at TEXT,
      consent_at TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS login_tokens (
      token TEXT PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS channels (
      id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, description TEXT NOT NULL, sort INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS posts (
      id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL REFERENCES channels(id),
      parent_id INTEGER REFERENCES posts(id), member_id INTEGER NOT NULL REFERENCES members(id),
      body TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      member_id INTEGER NOT NULL REFERENCES members(id), reason TEXT NOT NULL,
      resolved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE(post_id, member_id)
    );
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, organiser TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
      start_date TEXT, end_date TEXT, venue TEXT, source_url TEXT NOT NULL, source_label TEXT NOT NULL DEFAULT 'Visit the organiser',
      group_label TEXT NOT NULL DEFAULT '', members_only INTEGER NOT NULL DEFAULT 0, verified_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS event_saves (
      event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
      member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      PRIMARY KEY (event_id, member_id)
    );
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY, employer TEXT NOT NULL, title TEXT NOT NULL, location TEXT NOT NULL DEFAULT '',
      speciality TEXT NOT NULL DEFAULT '', seniority TEXT NOT NULL DEFAULT '', remote INTEGER NOT NULL DEFAULT 0,
      source_url TEXT NOT NULL, expires_at TEXT, posted_by INTEGER REFERENCES members(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS job_clicks (
      id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE, created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS resources (
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, url TEXT NOT NULL,
      summary TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      text TEXT NOT NULL, link TEXT NOT NULL DEFAULT '', read INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  return db;
}
