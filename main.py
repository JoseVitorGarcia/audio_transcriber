import argparse
from src.transcriber import AudioTranscriber


def main():
    parser = argparse.ArgumentParser(description="Transcrever áudios automaticamente")

    parser.add_argument("--input", default="audios")
    parser.add_argument("--output", default="transcricoes")
    parser.add_argument("--temp", default="temp")
    parser.add_argument("--model", default="medium")

    args = parser.parse_args()

    transcriber = AudioTranscriber(
        model_name=args.model
    )

    transcriber.process_directory(
        input_dir=args.input,
        output_dir=args.output,
        temp_dir=args.temp
    )


if __name__ == "__main__":
    main()