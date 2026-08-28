from __future__ import annotations

from followdesk.app import create_app


def main() -> None:
    app = create_app()
    result = app.state.process_followups()
    print(f"Processed {result['processed']} messages. Failed: {result['failed']}.")


if __name__ == "__main__":
    main()
