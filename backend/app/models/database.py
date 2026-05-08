from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    versions = relationship("ResumeVersion", back_populates="project")

class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    version_number = Column(Integer, default=1)
    tex_content = Column(Text)
    pdf_path = Column(String, nullable=True)
    analysis_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="versions")
    edits = relationship("UserEdit", back_populates="version")

class UserEdit(Base):
    __tablename__ = "user_edits"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("resume_versions.id"))
    instructions = Column(Text)
    result_tex = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    version = relationship("ResumeVersion", back_populates="edits")
