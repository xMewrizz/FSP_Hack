from enum import Enum


class UserRole(str, Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"


class Grade(str, Enum):
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"


class WorkFormat(str, Enum):
    REMOTE = "remote"
    OFFICE = "office"
    HYBRID = "hybrid"


class InvitationStatus(str, Enum):
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TestSessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    CODE = "code"


SPECIALIZATIONS = [
    "Backend",
    "Frontend",
    "Fullstack",
    "Mobile",
    "DevOps / SRE",
    "Data Science / ML",
    "QA / Testing",
    "System Programming / C++",
    "GameDev",
]
