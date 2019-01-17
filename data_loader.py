import tensorflow as tf
import pandas as pd
import numpy as np

from typing import Tuple
from config import Config


def get_datasets(
    config: Config, cat_before_window: bool = False
) -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]:
    """
    Returns X and y of the data passed as config.

    Parameters
    ----------
    config : Config
    cat_before_window : bool
        Whether to concatenate the files before transforming it
        into windows

    Returns
    -------
    train_d : tensorflow.data.Dataset(tuples)
        The tuples are
            X : (config.batch_size, config.n, config.T)
            y : (config.batch_size, config.T, 1)
    val_d
    test_d

    Usage
    -----

    Graph Mode:
    ```
    dataset = get_train_test_dataset(config)
    dataset = dataset.batch(batch_size) # .shuffle() if necessary
    iterator = dataset.make_initializable_iterator()
    next_element = iterator.get_next()
    for _ in range(epochs):
        sess.run(iterator.initializer)
        while True:
            try:
                sess.run(next_element)
            except tf.errors.OutOfRangeError:
                break

        # [Perform end-of-epoch calculations here.]
    ```

    Eager Mode:
    ```
        dataset = get_train_test_dataset(config)
        it = dataset.batch(batch_size)
        for x, y in it:
            print(x, y)
    ```
    """

    def window(df, size, driving_series, target_series):
        X = df[driving_series].values
        y = df[target_series].values
        X_T = []
        y_T = []
        for i in range(len(X) - size):
            X_T.append(X[i : i + size])
            y_T.append(y[i : i + size])

        return np.array(X_T), np.array(y_T)

    path = config.data_paths[0]

    with open(path) as f:
        header = f.readline().strip().split(config.sep)

    usecols = [col for col in header if col not in config.drop_cols]

    driving_series = [col for col in usecols if col not in config.target_cols]

    config.n = len(driving_series)
    dfs = []
    for path in config.data_paths:
        dfs.append(pd.read_csv(path, sep=config.sep, usecols=usecols))

    df = None
    X_T = None
    y_T = None
    if cat_before_window:
        df = pd.concat(dfs)
        X_T, y_T = window(df, config.T, driving_series, config.target_cols)
        X_T = X_T.transpose((0, 2, 1))
    else:
        X_Ts = []
        y_Ts = []
        for df in dfs:
            X_T, y_T = window(df, config.T, driving_series, config.target_cols)
            X_T = X_T.transpose((0, 2, 1))
            X_Ts.append(X_T)
            y_Ts.append(np.squeeze(y_T))
        X_T = np.vstack(X_Ts)
        y_T = np.vstack(y_Ts)
    train_size = int(len(X_T) * config.train_ratio)
    val_size = int(((1 - config.train_ratio) / 2) * len(X_T))
    test_size = val_size

    dataset = tf.data.Dataset.zip((
        tf.data.Dataset.from_tensor_slices(X_T),
        tf.data.Dataset.from_tensor_slices(y_T),
    ))

    train_dataset = dataset.take(train_size)
    val_dataset = dataset.skip(train_size).take(val_size)
    test_dataset = dataset.skip(train_size + val_size).take(test_size)
    return train_dataset, val_dataset, test_dataset


# Test
if __name__ == "__main__":
    tf.enable_eager_execution()
    with open("conf/NASDAQ100.json") as f:
        config = Config.from_json(f.read())

    tr, val, te = get_datasets(config)

    it = tr.make_one_shot_iterator()
    lit = val.make_one_shot_iterator()
    tit = te.make_one_shot_iterator()
    print(f"len(list(it)) {len(list(it))}")
    print(f"len(list(lit)) {len(list(lit))}")
    print(f"len(list(tit)) {len(list(tit))}")

"""

it = data_w.make_one_shot_iterator()
for x in it:
    print(x)
"""
