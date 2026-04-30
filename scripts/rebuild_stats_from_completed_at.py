import sqlite3


def main() -> None:
    conn = sqlite3.connect("data/coapi.db")
    c = conn.cursor()

    c.execute("UPDATE request_logs SET completed_at = created_at WHERE completed_at IS NULL")

    for table in ["stats_hourly", "stats_daily", "stats_model", "stats_channel", "stats_token"]:
        c.execute(f"DELETE FROM {table}")

    c.execute(
        """
        INSERT INTO stats_daily (date, request_count, success_count, fail_count, input_tokens, output_tokens)
        SELECT
            strftime('%Y-%m-%d', coalesce(completed_at, created_at)),
            COUNT(*),
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END),
            SUM(COALESCE(prompt_tokens, 0)),
            SUM(COALESCE(completion_tokens, 0))
        FROM request_logs
        GROUP BY strftime('%Y-%m-%d', coalesce(completed_at, created_at))
        """
    )

    c.execute(
        """
        INSERT INTO stats_hourly (hour, request_count, success_count, fail_count, input_tokens, output_tokens)
        SELECT
            strftime('%Y-%m-%d_%H', coalesce(completed_at, created_at)),
            COUNT(*),
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END),
            SUM(COALESCE(prompt_tokens, 0)),
            SUM(COALESCE(completion_tokens, 0))
        FROM request_logs
        GROUP BY strftime('%Y-%m-%d_%H', coalesce(completed_at, created_at))
        """
    )

    c.execute(
        """
        INSERT INTO stats_model (model_name, request_count, input_tokens, output_tokens)
        SELECT
            model,
            COUNT(*),
            SUM(COALESCE(prompt_tokens, 0)),
            SUM(COALESCE(completion_tokens, 0))
        FROM request_logs
        WHERE model IS NOT NULL AND model != ''
        GROUP BY model
        """
    )

    c.execute(
        """
        INSERT INTO stats_channel (channel_id, request_count, success_count, fail_count, input_tokens, output_tokens, avg_first_token_ms)
        SELECT
            channel_id,
            COUNT(*),
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END),
            SUM(COALESCE(prompt_tokens, 0)),
            SUM(COALESCE(completion_tokens, 0)),
            CAST(AVG(COALESCE(first_token_ms, 0)) AS INTEGER)
        FROM request_logs
        WHERE channel_id IS NOT NULL
        GROUP BY channel_id
        """
    )

    c.execute(
        """
        INSERT INTO stats_token (token_id, request_count, input_tokens, output_tokens)
        SELECT
            token_id,
            COUNT(*),
            SUM(COALESCE(prompt_tokens, 0)),
            SUM(COALESCE(completion_tokens, 0))
        FROM request_logs
        WHERE token_id IS NOT NULL
        GROUP BY token_id
        """
    )

    conn.commit()

    print("today daily:", c.execute("SELECT date, request_count, input_tokens, output_tokens FROM stats_daily WHERE date = date('now')").fetchall())
    print("today request_logs:", c.execute("SELECT date(coalesce(completed_at, created_at)), count(*), sum(prompt_tokens), sum(completion_tokens) FROM request_logs WHERE date(coalesce(completed_at, created_at)) = date('now') GROUP BY date(coalesce(completed_at, created_at))").fetchall())

    conn.close()


if __name__ == "__main__":
    main()
