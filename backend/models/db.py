"""
BUSTAGO Backend -- DB 연결 헬퍼
MySQL 우선, 연결 실패 시 SQLite 폴백.
"""

import sqlite3
import os
from contextlib import contextmanager

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

from backend.config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, SQLITE_PATH,
)

_use_sqlite = False


def _try_mysql():
    """MySQL 연결 시도. 실패하면 None 반환."""
    if not HAS_PYMYSQL:
        return None
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return conn
    except Exception:
        return None


def _get_sqlite():
    """SQLite 폴백 연결."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_sqlite_schema():
    """SQLite 테이블이 없으면 생성."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    if not os.path.exists(schema_path):
        return
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = f.read()
    # MySQL 전용 구문을 SQLite 호환으로 변환
    sql = raw
    # MySQL `INT AUTO_INCREMENT PRIMARY KEY` → SQLite `INTEGER PRIMARY KEY`
    # SQLite 자동증가는 정확히 `INTEGER`일 때만 동작 — `INT`로 두면 id=NULL이 된다.
    sql = sql.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY")
    sql = sql.replace("AUTO_INCREMENT", "")
    sql = sql.replace("TINYINT", "INTEGER")
    sql = sql.replace("DECIMAL(10,7)", "REAL")
    sql = sql.replace("DECIMAL(4,1)", "REAL")
    sql = sql.replace("JSON", "TEXT")
    sql = sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TEXT DEFAULT (datetime('now'))")
    sql = sql.replace("ENGINE=InnoDB DEFAULT CHARSET=utf8mb4", "")
    sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
    conn = _get_sqlite()
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def init_db():
    """앱 기동 시 DB 연결을 확인하고 모드를 결정."""
    global _use_sqlite
    conn = _try_mysql()
    if conn is not None:
        conn.close()
        _use_sqlite = False
        print("[DB] MySQL 연결 성공")
    else:
        _use_sqlite = True
        _init_sqlite_schema()
        print("[DB] MySQL 연결 실패 -- SQLite 폴백 사용")


def is_sqlite():
    return _use_sqlite


@contextmanager
def get_conn():
    """커넥션 컨텍스트 매니저."""
    if _use_sqlite:
        conn = _get_sqlite()
    else:
        conn = _try_mysql()
        if conn is None:
            conn = _get_sqlite()
    try:
        yield conn
    finally:
        conn.close()


def _adapt_sql(sql):
    """SQLite용 ? 플레이스홀더를 PyMySQL용 %s로 변환."""
    if not _use_sqlite:
        return sql.replace("?", "%s")
    return sql


def fetchall(sql, params=None):
    """SELECT 결과를 dict 리스트로 반환."""
    with get_conn() as conn:
        if _use_sqlite:
            cur = conn.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        else:
            with conn.cursor() as cur:
                cur.execute(_adapt_sql(sql), params or ())
                return cur.fetchall()


def fetchone(sql, params=None):
    """SELECT 결과 1건을 dict로 반환."""
    with get_conn() as conn:
        if _use_sqlite:
            cur = conn.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None
        else:
            with conn.cursor() as cur:
                cur.execute(_adapt_sql(sql), params or ())
                return cur.fetchone()


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE 실행."""
    with get_conn() as conn:
        if _use_sqlite:
            conn.execute(sql, params or ())
            conn.commit()
        else:
            with conn.cursor() as cur:
                cur.execute(_adapt_sql(sql), params or ())
            conn.commit()
