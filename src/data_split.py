import pandas as pd


def create_time_split(
    input_path="data/raw/train.csv",
    train_path="data/processed/train.csv",
    validation_path="data/processed/validation.csv",
    train_ratio=0.8
):
    df = pd.read_csv(input_path)

    df = df.sort_values("timestamp").reset_index(drop=True)

    split_index = int(len(df) * train_ratio)

    train_df = df.iloc[:split_index].copy()
    validation_df = df.iloc[split_index:].copy()

    train_df.to_csv(train_path, index=False)
    validation_df.to_csv(validation_path, index=False)

    print("TRAIN SHAPE:", train_df.shape)
    print("VALIDATION SHAPE:", validation_df.shape)

    print("\nTRAIN LABELS:")
    print(train_df["label"].value_counts())

    print("\nVALIDATION LABELS:")
    print(validation_df["label"].value_counts())

    print("\nTRAIN TIME:")
    print(train_df["timestamp"].min(), "->", train_df["timestamp"].max())

    print("\nVALIDATION TIME:")
    print(
        validation_df["timestamp"].min(),
        "->",
        validation_df["timestamp"].max()
    )


if __name__ == "__main__":
    create_time_split()