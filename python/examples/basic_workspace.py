import mercurio


def main() -> None:
    with mercurio.open("examples/src/examples/Camera Example") as model:
        print(model.parts())


if __name__ == "__main__":
    main()
