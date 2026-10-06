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
