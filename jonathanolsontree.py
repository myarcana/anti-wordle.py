from wordle import *


class JonathanOlsonTree:
    def __init__(self, json_path: str):
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        self.tree = data

    def guess(self) -> str:
        try:
            return self.tree['guess']
        except TypeError:
            return self.tree
        except KeyError:
            raise NoGuessesException()

    def feedback(self, guess: str, answer: list[Status]):
        key = ''.join({Status.NotPresent: '0', Status.Present: '1', Status.Placed: '2'}[status] for status in answer)
        try:
            self.tree = self.tree['map'][key]
        except:
            self.tree = {}


if __name__ == '__main__':
    play_game(lambda: JonathanOlsonTree('salet.tree.hard.json'))
