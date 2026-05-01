import time


def simulate_stream(data, delay=0.05, max_rows=None):
    """
    Yield one row at a time to simulate streaming data.

    This intentionally stays simple: no async, no queues, just a controlled
    replay of the uploaded dataset.
    """
    stream_data = data.head(max_rows) if max_rows else data

    for index, row in stream_data.iterrows():
        time.sleep(delay)
        yield index, row, stream_data.loc[:index]


def simulate_stream_batches(data, batch_size=10, delay=0.05, max_rows=None):
    """
    Yield data in small batches to reduce UI redraw cost.

    Streamlit rerenders charts relatively expensively, so updating once per
    batch is much smoother than updating once per row.
    """
    stream_data = data.head(max_rows) if max_rows else data
    total_rows = len(stream_data)

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        time.sleep(delay)

        current_data = stream_data.iloc[:end]
        current_batch = stream_data.iloc[start:end]
        current_row = stream_data.iloc[end - 1]

        yield {
            "batch_number": (start // batch_size) + 1,
            "total_batches": (total_rows + batch_size - 1) // batch_size,
            "start_row": start + 1,
            "end_row": end,
            "total_rows": total_rows,
            "current_row": current_row,
            "current_batch": current_batch,
            "current_data": current_data,
        }
