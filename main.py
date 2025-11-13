"""Entry point for the refactored Pygame project."""

from game_core.game import Game


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
