def create_progress_bar(percent, length=20):
    filled_length = int(length * percent // 100)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f'[{bar}] {percent:.0f}%'