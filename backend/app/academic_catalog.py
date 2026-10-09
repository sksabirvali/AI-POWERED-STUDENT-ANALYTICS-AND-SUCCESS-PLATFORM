from datetime import date


SUBJECTS_BY_SEMESTER = {
    1: [
        "Engineering Mathematics I",
        "Applied Physics",
        "Programming Fundamentals",
        "Basic Electrical Engineering",
        "Engineering Graphics",
        "Communication Skills",
    ],
    2: [
        "Engineering Mathematics II",
        "Applied Chemistry",
        "Data Structures",
        "Basic Electronics",
        "Environmental Science",
        "Professional Communication",
    ],
    3: [
        "Discrete Mathematics",
        "Digital Logic Design",
        "Object-Oriented Programming",
        "Computer Organization",
        "Probability and Statistics",
        "Data Structures and Algorithms",
    ],
    4: [
        "Design and Analysis of Algorithms",
        "Database Management Systems",
        "Operating Systems",
        "Software Engineering",
        "Signals and Systems",
        "Microprocessors",
    ],
    5: [
        "Computer Networks",
        "Theory of Computation",
        "Compiler Design",
        "Web Technologies",
        "Machine Learning",
        "Department Elective I",
    ],
    6: [
        "Artificial Intelligence",
        "Cloud Computing",
        "Information Security",
        "Mobile Application Development",
        "Distributed Systems",
        "Department Elective II",
    ],
    7: [
        "Big Data Analytics",
        "Internet of Things",
        "DevOps Engineering",
        "Data Mining",
        "Project Phase I",
        "Department Elective III",
    ],
    8: [
        "Professional Ethics",
        "Entrepreneurship",
        "Project Phase II",
        "Industry Internship",
        "Department Elective IV",
        "Emerging Technologies",
    ],
}

LABS_BY_SEMESTER = {
    1: ["Engineering Physics Lab", "Programming Lab I", "Workshop Practice"],
    2: ["Applied Chemistry Lab", "Data Structures Lab", "Electronics Lab"],
    3: ["Object-Oriented Programming Lab", "Digital Systems Lab", "Algorithms Lab"],
    4: ["Database Systems Lab", "Operating Systems Lab", "Microprocessors Lab"],
    5: ["Computer Networks Lab", "Compiler Design Lab", "Web Technologies Lab"],
    6: ["Artificial Intelligence Lab", "Cloud Computing Lab", "Mobile Applications Lab"],
    7: ["Big Data Lab", "Internet of Things Lab", "Project Lab I"],
    8: ["Advanced Computing Lab", "Project Lab II", "Internship Evaluation"],
}


def academic_year_for_semester(semester: int, current_year: int | None = None) -> int:
    if not 1 <= semester <= 8:
        raise ValueError("semester must be between 1 and 8")
    year = current_year or date.today().year
    return year - ((8 - semester) // 2)


def component_name(semester: int, component_type: str, index: int) -> str:
    components = SUBJECTS_BY_SEMESTER[semester] if component_type == "subject" else LABS_BY_SEMESTER[semester]
    return components[index - 1]
