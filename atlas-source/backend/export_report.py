from engines.markdown_report_engine import MarkdownReportEngine


def main():
    report_engine = MarkdownReportEngine()
    report_path = report_engine.export_latest_report()

    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
