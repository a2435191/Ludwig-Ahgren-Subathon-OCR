def seconds_to_string(n: int) -> str:
    hour = int(n // 3600)
    seconds = int(n % 60)
    minutes = int((n // 60) % 60)
    return f"{hour:03}:{minutes:02}:{seconds:02}"