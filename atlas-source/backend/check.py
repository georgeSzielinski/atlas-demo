import compileall
import sys

from backend.status import MODULES_TO_CHECK, import_status


PATHS_TO_COMPILE = [
    "ai",
    "api",
    "atlas",
    "backend",
    "core",
    "database",
    "engines",
    "market",
    "models",
    "portfolio",
    "services",
    "trading",
]


def run_import_checks():
    print("Imports:")

    passed = True

    for module_name in MODULES_TO_CHECK:
        status = import_status(module_name)
        print(f"- {module_name}: {status}")

        if status != "PASS":
            passed = False

    return passed


def run_compile_checks():
    print("Compile:")

    passed = True

    for path in PATHS_TO_COMPILE:
        result = compileall.compile_dir(
            path,
            quiet=1,
            force=False
        )
        status = "PASS" if result else "FAIL"
        print(f"- {path}: {status}")

        if not result:
            passed = False

    if passed:
        print("PASS")
    else:
        print("FAIL")

    return passed


def main():
    print("ATLAS CHECK")
    print()

    imports_passed = run_import_checks()
    print()
    compile_passed = run_compile_checks()

    if imports_passed and compile_passed:
        sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()
