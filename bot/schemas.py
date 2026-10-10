"""Pydantic schemas describing the structure of a tender analysis."""
from typing import List, Optional

from pydantic import BaseModel, Field


class Deadlines(BaseModel):
    submission_deadline: Optional[str] = None
    clarification_deadline: Optional[str] = None
    other_dates: List[str] = Field(default_factory=list)


class EvaluationCriterion(BaseModel):
    criterion: str
    weight: Optional[str] = None


class Budget(BaseModel):
    estimated_value: Optional[str] = None
    currency: Optional[str] = None
    funding_source: Optional[str] = None


class TenderAnalysis(BaseModel):
    """Structured representation of key tender information."""

    summary: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)
    deadlines: Deadlines = Field(default_factory=Deadlines)
    required_documents: List[str] = Field(default_factory=list)
    eligibility_criteria: List[str] = Field(default_factory=list)
    evaluation_criteria: List[EvaluationCriterion] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    important_clauses: List[str] = Field(default_factory=list)
