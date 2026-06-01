import os

import machineLearning as ML
import utilities as UM


def main_trainning_app():
    settings = UM.load_settings()
    [x_train, y_train, x_test, y_test] = ML.construct_dataset(
        settings["DATA_PATH"], int(settings["IMG_SIZE"]), float(settings["TTS"])
    )
    print(f"Training set: {len(x_train)} images, validation set: {len(x_test)} images")
    if len(x_train) == 0:
        print("No training images available. Run SCRAPE more before training.")
        return

    model = ML.build_model(int(settings["IMG_SIZE"]))
    if os.path.exists(settings["MODELPATH"]):
        try:
            model.load_weights(settings["MODELPATH"])
            print("Loaded existing model weights")
        except Exception as e:
            print(f"Couldn't load existing model: {e}")

    model = ML.train_model(
        x_train, y_train, int(settings["IMG_SIZE"]), int(settings["BATCH_SIZE"]), int(settings["EPOCHS"])
    )

    if len(x_test) > 0:
        y_preads = model.predict(x_test)
        y_preads_binary = (y_preads > 0.5).astype(int)
        accuracy = ML.return_accuracy(y_test, y_preads_binary)
        print(f"The model is {accuracy * 100:.2f}% accurate on validation set")
    else:
        print("No validation data — skipping accuracy report")

    model.save_weights(settings["MODELPATH"])
    print(f"Weights saved to {settings['MODELPATH']}")


if __name__ == "__main__":
    main_trainning_app()
