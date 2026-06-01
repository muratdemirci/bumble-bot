import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers
from tensorflow.keras.applications import EfficientNetB0
from sklearn.metrics import accuracy_score
import pandas as pd
import os
from skimage import io
from skimage.transform import resize
import random
import numpy as np


def return_test_train(split_value):
    rval = random.random()
    if rval >= split_value:
        return 1  # 1 means its validation data
    else:
        return 0  # zero means its training data


def encode_one_hot(label):
    if label == "positive":
        return 1
    elif label == "negetive":
        return 0


def _collect_index_rows(DATA_PATH):
    """Walk DATA_PATH/<session>/*.csv, return a DataFrame of all labelled profiles
    with an extra 'session_dir' column so we know where each profile's images live."""
    frames = []
    if not os.path.isdir(DATA_PATH):
        raise FileNotFoundError(
            f"DATA_PATH '{DATA_PATH}' does not exist. Run SCRAPE first."
        )
    for session in os.listdir(DATA_PATH):
        session_dir = os.path.join(DATA_PATH, session)
        if not os.path.isdir(session_dir):
            continue
        for fname in os.listdir(session_dir):
            if not fname.endswith(".csv"):
                continue
            csv_path = os.path.join(session_dir, fname)
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"  ! Skipping unreadable CSV {csv_path}: {e}")
                continue
            if "profile" not in df.columns or "outcome" not in df.columns:
                continue
            df = df[["profile", "outcome"]].copy()
            df["session_dir"] = session_dir
            frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"No labelled profiles found under '{DATA_PATH}'. Run SCRAPE first."
        )
    return pd.concat(frames, ignore_index=True)


def construct_dataset(DATA_PATH, IMG_SIZE, test_train_split):
    data_index = _collect_index_rows(DATA_PATH)
    x_train, y_train, x_test, y_test = [], [], [], []
    counter = 0
    skipped_profiles = 0
    for _, row in data_index.iterrows():
        image_path_folder = os.path.join(row["session_dir"], row["profile"])
        if not os.path.isdir(image_path_folder):
            skipped_profiles += 1
            continue
        label = encode_one_hot(row["outcome"])
        if label is None:
            continue
        for file in os.listdir(image_path_folder):
            fp = os.path.join(image_path_folder, file)
            try:
                image = io.imread(fp)
                img = resize(image, (IMG_SIZE, IMG_SIZE))
                if img.ndim == 2:
                    img = np.stack([img] * 3, axis=-1)
                elif img.shape[-1] == 4:
                    img = img[..., :3]
            except Exception as e:
                print(f"  ! Skipping unreadable image {fp}: {e}")
                continue
            if return_test_train(test_train_split) == 0:
                x_train.append(img)
                y_train.append(label)
            else:
                x_test.append(img)
                y_test.append(label)
            counter += 1

    print(f"A total of {counter} images were processed across {len(data_index)} profiles "
          f"({skipped_profiles} profiles skipped — folder missing)")

    return [np.asarray(x_train), np.asarray(y_train), np.asarray(x_test), np.asarray(y_test)]


def build_model(IMG_SIZE):
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    img_augmentation = Sequential(
        [
            layers.RandomRotation(factor=0.10),
            layers.RandomTranslation(height_factor=0.1, width_factor=0.1),
        ],
        name="img_augmentation",
    )
    x = img_augmentation(inputs)
    model = EfficientNetB0(include_top=False, input_tensor=x, weights="imagenet")

    # Freeze the pretrained weights
    model.trainable = False

    # Rebuild top
    x = layers.GlobalAveragePooling2D(name="avg_pool")(model.output)
    x = layers.BatchNormalization()(x)

    top_dropout_rate = 0.2
    x = layers.Dropout(top_dropout_rate, name="top_dropout")(x)
    outputs = layers.Dense(1, activation="sigmoid", name="pred")(x)  # the otput layers are hardcoded
    # cause you cant sorta like a person on bumble

    # Compile
    model = tf.keras.Model(inputs, outputs, name="EfficientNet")
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
    model.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train_model(x_train, y_train, IMG_SIZE, BATCH_SIZE, epochs):
    strategy = tf.distribute.MirroredStrategy()
    with strategy.scope():
        model = build_model(IMG_SIZE)
    model.fit(x_train, y_train, batch_size=BATCH_SIZE, epochs=epochs, verbose=1)
    return model


def make_prediction(pictures, model):
    prediction = model.predict(np.asarray(pictures))
    avg = np.mean(prediction)
    print(f"Average weight of prediction {avg}")
    return avg

def make_decision(pred_avg, thresh):
    print(f"Making a decision, accuracy of {pred_avg}, threshold set at {thresh}")
    if pred_avg > thresh:
        return 1
    else:
        return 0

def load_images_for_prediction(DATA_PATH, IMG_SIZE, profile):
    pictureDir = os.path.join(os.getcwd(), DATA_PATH, profile)
    # load all the pictures into an array
    pictures = []
    for file in os.listdir(pictureDir):
        fp = os.path.join(pictureDir, file)
        # then load them using sk image
        image = io.imread(fp)
        img = resize(image, (IMG_SIZE, IMG_SIZE))
        pictures.append(img)
    return pictures


def return_accuracy(ytrue, ypreads):
    return accuracy_score(ytrue, ypreads)
