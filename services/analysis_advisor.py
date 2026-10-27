from dataclasses import dataclass


@dataclass(frozen=True)
class SkillAction:
    skill: str
    practice_activity: str
    project_idea: str
    learning_resource: str
    learning_url: str | None


SKILL_GUIDANCE = {
    "AWS": (
        "Deploy a small service and document its storage, compute, and access settings.",
        "Host a simple portfolio or API and write a short architecture note.",
        "AWS Skill Builder",
        "https://skillbuilder.aws/",
    ),
    "C#": (
        "Practice types, collections, methods, and exception handling in small console exercises.",
        "Build a command-line application tracker with input validation and tests.",
        "C# learning paths",
        "https://learn.microsoft.com/en-us/dotnet/csharp/",
    ),
    "C++": (
        "Practice functions, containers, references, and memory-safe resource handling.",
        "Build a command-line study planner with search and file persistence.",
        "LearnCpp tutorials",
        "https://www.learncpp.com/",
    ),
    "CSS": (
        "Recreate a responsive layout and test it at narrow and wide viewport sizes.",
        "Build an accessible, responsive portfolio page for two projects.",
        "MDN CSS learning module",
        "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics",
    ),
    "Docker": (
        "Containerize a small app and practice building, running, and reading its logs.",
        "Package a local dashboard with a clear setup guide and health check.",
        "Docker Get Started",
        "https://docs.docker.com/get-started/",
    ),
    "Git": (
        "Practice small commits, branches, merges, and resolving a simple conflict.",
        "Version-control a project with focused commits and a useful README.",
        "Pro Git book",
        "https://git-scm.com/book/en/v2",
    ),
    "HTML": (
        "Structure a page with semantic headings, links, forms, and accessible labels.",
        "Build a multi-section portfolio page with a working project list.",
        "MDN HTML learning module",
        "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content",
    ),
    "Java": (
        "Practice classes, collections, interfaces, and exception handling with short exercises.",
        "Build a command-line interview question organizer with searchable categories.",
        "dev.java learning materials",
        "https://dev.java/learn/",
    ),
    "JavaScript": (
        "Practice arrays, functions, DOM events, and asynchronous requests in small exercises.",
        "Build a browser-based deadline tracker with filters and local sample data.",
        "MDN JavaScript Guide",
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
    ),
    "Machine Learning": (
        "Compare a simple baseline with a trained model and inspect precision and recall.",
        "Classify a small public dataset and document limitations and possible bias.",
        "scikit-learn tutorials",
        "https://scikit-learn.org/stable/tutorial/index.html",
    ),
    "Node.js": (
        "Build a small HTTP endpoint and practice request validation and error responses.",
        "Create a local API for listing and filtering sample internship records.",
        "Node.js Learn",
        "https://nodejs.org/en/learn",
    ),
    "Python": (
        "Practice functions, collections, file handling, and tests with short exercises.",
        "Build a command-line tool that summarizes a CSV of fictional applications.",
        "Python Tutorial",
        "https://docs.python.org/3/tutorial/",
    ),
    "REST APIs": (
        "Practice HTTP methods, status codes, JSON requests, and input validation.",
        "Build a small API for fictional opportunities with search and filtering.",
        "MDN HTTP overview",
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
    ),
    "React": (
        "Practice components, props, state, and rendering a filtered list.",
        "Build a small application tracker with status filters and a detail view.",
        "React Learn",
        "https://react.dev/learn",
    ),
    "SQL": (
        "Practice SELECT, filtering, joins, grouping, and parameterized queries.",
        "Model fictional applications in SQLite and answer progress questions with queries.",
        "SQLBolt interactive lessons",
        "https://sqlbolt.com/",
    ),
    "SQLite": (
        "Practice table design, constraints, indexes, transactions, and parameterized queries.",
        "Build a local tracker with create, edit, list, and delete operations.",
        "SQLite documentation",
        "https://www.sqlite.org/docs.html",
    ),
    "TypeScript": (
        "Add types to a small JavaScript data model and handle optional values.",
        "Build a typed opportunity search page with validated filters.",
        "TypeScript Handbook",
        "https://www.typescriptlang.org/docs/handbook/intro.html",
    ),
    "pandas": (
        "Load a CSV, clean missing values, group records, and validate the output.",
        "Analyze a fictional application dataset and chart its status breakdown.",
        "pandas getting started tutorials",
        "https://pandas.pydata.org/docs/getting_started/intro_tutorials/",
    ),
    "scikit-learn": (
        "Fit a baseline model, split data correctly, and compare evaluation metrics.",
        "Build a small text classifier and document its errors and limitations.",
        "scikit-learn tutorials",
        "https://scikit-learn.org/stable/tutorial/index.html",
    ),
}


def build_skill_action_plan(missing_skills: tuple[str, ...]) -> tuple[SkillAction, ...]:
    """Create deterministic practice guidance for skills not detected in the resume."""
    action_plan = []
    for skill in missing_skills:
        guidance = SKILL_GUIDANCE.get(skill)
        if guidance is None:
            action_plan.append(
                SkillAction(
                    skill=skill,
                    practice_activity=f"Choose one small task that uses {skill} and complete it using its official documentation.",
                    project_idea=f"Build a small, testable project that uses {skill} and document your decisions.",
                    learning_resource=f"Official documentation and beginner tutorials for {skill}",
                    learning_url=None,
                )
            )
        else:
            practice_activity, project_idea, learning_resource, learning_url = guidance
            action_plan.append(
                SkillAction(
                    skill=skill,
                    practice_activity=practice_activity,
                    project_idea=project_idea,
                    learning_resource=learning_resource,
                    learning_url=learning_url,
                )
            )
    return tuple(action_plan)