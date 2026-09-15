import os

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

_HERE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

# 이 앱은 Supabase의 다른 프로젝트(다른 앱)와 같은 Postgres 인스턴스를 공유할 수도 있으므로,
# 테이블을 전용 스키마 안에 격리해 이름 충돌(예: users/todos)을 피한다.
SCHEMA = "ai_sales_assistant"

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        conn.commit()
    metadata = MetaData(schema=SCHEMA)
else:
    # DATABASE_URL이 없으면(로컬 개발) 프로젝트 폴더의 SQLite 파일을 그대로 사용한다.
    DB_PATH = os.path.join(_HERE, "sales_assistant.db")
    engine = create_engine(
        f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
    )
    metadata = MetaData()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base(metadata=metadata)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
