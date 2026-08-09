import time
from typing import Any

import jdatetime
import pandas as pd
import requests


KALA_DICT = {
    "Sekeh_Bahar_Azadi": "sekeb",
    "dollar": "price_dollar_rl",
    "Naft": "oil",
    "Tala_24": "geram24",
    "Tala_18": "geram18",
    "Sekeh_grame": "gerami",
}

BASE_URL = "https://www.tgju.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.tgju.org/",
}


def generate_jalali_dates(
    start_date: jdatetime.date,
    end_date: jdatetime.date,
):
    current_date = start_date

    while current_date <= end_date:
        yield current_date
        current_date += jdatetime.timedelta(days=1)


def extract_record(data: Any) -> dict | None:

    if isinstance(data, list):
        if not data:
            return None

        return data[0] if isinstance(data[0], dict) else None

    if isinstance(data, dict):
        if "data" in data:
            inner_data = data["data"]

            if isinstance(inner_data, dict):
                return inner_data

            if (
                isinstance(inner_data, list)
                and inner_data
                and isinstance(inner_data[0], dict)
            ):
                return inner_data[0]

        return data

    return None


def get_data(
    session: requests.Session,
    product_name: str,
    symbol: str,
    jalali_date: jdatetime.date,
) -> dict | None:

    year = jalali_date.year
    month = jalali_date.month
    day = jalali_date.day

    date_string = f"{year:04d}/{month:02d}/{day:02d}"

    params = {
        "act": "archive-tool",
        "noview": "",
        "client": "ajax",
        "v": 200,
        "name": symbol,
        "year": year,
        "month": month,
        "day": day,
    }

    try:
        response = session.get(
            BASE_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print(
            f"Request failed: {product_name} | "
            f"{date_string} | {error}"
        )
        return None

    try:
        data = response.json()

    except requests.exceptions.JSONDecodeError:
        print(
            f"Invalid JSON: {product_name} | "
            f"{date_string}"
        )
        print(response.text[:300])
        return None

    record = extract_record(data)

    if not record:
        return None

    price_fields = [
        record.get("price"),
        record.get("open"),
        record.get("max"),
        record.get("min"),
    ]

    if all(value is None for value in price_fields):
        return None

    return {
        "product_name": product_name,
        "symbol": symbol,
        "jalali_date": date_string,
        "jalali_year": year,
        "jalali_month": month,
        "jalali_day": day,
        "id": record.get("id"),
        "item_id": record.get("item_id"),
        "open": record.get("open"),
        "value": record.get("value"),
        "max": record.get("max"),
        "min": record.get("min"),
        "price": record.get("price"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def collect_data_between_dates(
    start_date: jdatetime.date,
    end_date: jdatetime.date,
    delay_seconds: float = 0.5,
) -> pd.DataFrame:

    collected_records = []

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for product_name, symbol in KALA_DICT.items():

            print(f"\nCollecting {product_name} ({symbol})")

            for jalali_date in generate_jalali_dates(
                start_date,
                end_date,
            ):

                record = get_data(
                    session=session,
                    product_name=product_name,
                    symbol=symbol,
                    jalali_date=jalali_date,
                )

                if record is not None:
                    collected_records.append(record)

                    print(
                        f"Collected: {product_name} | "
                        f"{record['jalali_date']} | "
                        f"{record['price']}"
                    )

                time.sleep(delay_seconds)

    return pd.DataFrame(collected_records)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    numeric_columns = [
        "id",
        "item_id",
        "open",
        "value",
        "max",
        "min",
        "price",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype(str)
                .str.replace(",", "", regex=False)
            )

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    for column in ["created_at", "updated_at"]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    df = df.drop_duplicates(
        subset=["symbol", "jalali_date"]
    )

    df = df.sort_values(
        [
            "symbol",
            "jalali_year",
            "jalali_month",
            "jalali_day",
        ]
    ).reset_index(drop=True)

    return df


def main() -> None:

    start_date = jdatetime.date(1404, 10, 1)
    end_date = jdatetime.date(1405, 2, 31)

    collecting_data = collect_data_between_dates(
        start_date=start_date,
        end_date=end_date,
        delay_seconds=0.5,
    )

    collecting_data = clean_dataframe(
        collecting_data
    )

    if collecting_data.empty:
        print("No data was collected.")
        return

    collecting_data.to_csv(
        "tgju_prices_1404-10-01_to_1405-02-31.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\nFinished.")
    print(f"Rows: {len(collecting_data):,}")
    print(collecting_data.head())


if __name__ == "__main__":
    main()