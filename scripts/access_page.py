"""Generate the accessibility settings page from its checked-in HTML source."""
from pathlib import Path
SOURCE = Path("templates/access.html")
TARGET = Path("reports/access.html")
def main():
    TARGET.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
if __name__ == "__main__":
    main()
