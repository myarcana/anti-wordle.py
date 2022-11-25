import math
import random

from enum import Enum
from typing import Callable, Protocol

from colorama import just_fix_windows_console, Fore, Back, Style, Cursor
from sshkeyboard import listen_keyboard, stop_listening


class Status(Enum):
    Unknown = 0
    NotPresent = 1
    Present = 2
    Placed = 3

    @property
    def fore(self):
        if self == Status.Unknown:
            return Fore.RESET
        elif self == Status.NotPresent:
            return Fore.RESET
        elif self == Status.Present:
            return Fore.BLACK
        elif self == Status.Placed:
            return Fore.BLACK

    @property
    def back(self):
        if self == Status.Unknown:
            return Back.RESET
        elif self == Status.NotPresent:
            return Back.BLACK
        elif self == Status.Present:
            return Back.YELLOW
        elif self == Status.Placed:
            return Back.GREEN

    def paint(self, text: str) -> str:
        return self.back + self.fore + text + Fore.RESET + Back.RESET


def concat_columns(iterable: list[str]) -> str:
    lines = []
    for line_parts in zip(*(item.splitlines() for item in iterable)):
        line = ''.join(line_parts)
        lines.append(line)
    return '\n'.join(lines)


tile_width = 5
tile_height = 3


def tile(letter: str, status: Status) -> str:
    if len(letter) != 1:
        raise ValueError(f"Only single characters can be tiled, not '{letter}'")
    left_pad = math.ceil((tile_width - 1) / 2)
    right_pad = math.floor((tile_width - 1) / 2)
    space = ' '
    lines = [space * tile_width, space * left_pad + letter + space * right_pad, space * tile_width]
    return '\n'.join(status.paint(line) for line in lines)


def big_tiles(word: str, statuses: list[Status]) -> str:
    return concat_columns(tile(letter, status) for letter, status in zip(word, statuses))


record_unit_width = 3


def inline_tiles(word: str, statuses: list[Status]) -> str:
    return ''.join(status.paint(' ' + letter + ' ') for letter, status in zip(word, statuses))


class UndoException(Exception):
    pass


def calc_answer(guess: str, word: str) -> list[Status]:
    answer = []
    letters_left = word
    for guessed_letter, real_letter in zip(guess, word):
        if guess == 'drill':
            print(guessed_letter, letters_left)
        if guessed_letter in letters_left:
            letters_left = letters_left.replace(guessed_letter, '', 1)
            if guessed_letter == real_letter:
                answer.append(Status.Placed)
            else:
                answer.append(Status.Present)
        else:
            answer.append(Status.NotPresent)
    return answer


class AnswerWizard:
    answer_statuses = [Status.NotPresent, Status.Present, Status.Placed]
    height = tile_height + 3
    left_margin_width = 0

    def __init__(self, guess: str, can_undo: bool, state: list[Status]=None):
        self.guess = guess
        self.cursor_pos = 0
        self.answer = None
        self.can_undo = can_undo
        self.undo_requested = False
        if self.can_undo:
            self.prompt = 'Use WASD to select and change the letters, press U to change the last entry:'
        else:
            self.prompt = 'Use WASD to select and change the letters:'
        if state == None:
            self.status_numbers = [0] * len(guess)
        else:
            self.status_numbers = [self.answer_statuses.index(status) for status in state]

    def generate_answer(self):
        r'''Based on the current state of self.status_numbers, what would the answer be?'''
        return [self.answer_statuses[i] for i in self.status_numbers]

    def input_answer(self) -> list[Status]:
        r'''Display an interactive prompt to get the information about the guess from the user.

        :returns: a mapping of the letters of self.word to their user-selected statuses of presence in the word
        '''
        self.draw()
        listen_keyboard(on_press=self.keypress, until='enter', sequential=True, delay_second_char=0, delay_other_chars=0)
        if self.undo_requested:
            raise UndoException()
        self.clear()
        self.answer = self.generate_answer()
        return self.answer

    def draw(self):
        print(self.prompt)
        tiles = []
        statuses = [self.answer_statuses[status_number] for status_number in self.status_numbers]
        left_margin = ''.join(' ' * self.left_margin_width + '\n' for _ in range(tile_height))
        print(concat_columns([left_margin, big_tiles(self.guess, statuses)]))
        print(' ' * self.left_margin_width + ' ' * self.cursor_pos * tile_width + '^' * tile_width + ' ' * tile_width * (len(self.guess) - 1 - self.cursor_pos))

    def clear(self):
        print(Cursor.UP(self.height))
        print(' ' * len(self.prompt))
        print('\n'.join(' ' * (self.left_margin_width + tile_width * len(self.guess)) for _ in range(tile_height)))
        print(' ' * (self.left_margin_width + tile_width * len(self.guess)))
        print(Cursor.UP(self.height))

    def redraw(self):
        print(Cursor.UP(self.height))
        self.draw()

    def keypress(self, key):
        left, right, up, down = zip('adws', 'hlkj')
        undo = ('u')
        if key in left:
            self.cursor_pos = (self.cursor_pos - 1) % len(self.guess)
        elif key in right:
            self.cursor_pos = (self.cursor_pos + 1) % len(self.guess)
        elif key in up:
            self.status_numbers[self.cursor_pos] = (self.status_numbers[self.cursor_pos] + 1) % len(self.answer_statuses)
        elif key in down:
            self.status_numbers[self.cursor_pos] = (self.status_numbers[self.cursor_pos] - 1) % len(self.answer_statuses)
        elif key in undo and self.can_undo:
            self.undo_requested = True
            stop_listening()
        self.redraw()


def ordinal(n: int) -> str:
    r'''The nth ordinal number, 0-indexed'''
    ordinals = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']
    try:
        return ordinals[n]
    except IndexError:
        n += 1
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        return str(n) + suffix


trash_talks = [
    '...? Yeah right.',
    ', like what...?',
    ", how's that for a first guess?",
    ', whaddaya think?',
    ', buddy.',
    ", and you'd better believe it.",
    '... take notes.',
    ", you wouldn't know about it.",
    ', inshallah.',
]


undoing_prompts = [
    "Okay, {turn_name} guess again. I guessed '{guess}', please correct your marking professor.",
    "Take a second look at my {turn_name} guess, '{guess}'. What do your elf eyes see?",
    "You've rewound time again, this time to the {turn_name} guess. How many times you gonna have to do this?",
    "You're changing history my friend, from the {turn_name} guess forward.",
]


class NoGuessesException(Exception):
    pass


class GuessingStrategy(Protocol):
    def guess(self) -> str:
        r'''Ask for the word the guessing strategy would like to submit based on its current knowledge.

        :returns: a word
        :raises NoGuessesException: when the guessing strategy cannot make any guesses based on the information fed back so far
        '''
        raise NotImplementedError()

    def feedback(self, guess: str, answer: list[Status]):
        raise NotImplementedError()


class RandomAssStrategy:
    def __init__(self, words: list[str]):
        self.words = words

    def guess(self):
        return random.choice(self.words)

    def feedback(self, guess: str, answer: list[Status]):
        pass


class TheStrongestStrategy:
    def __init__(self, words: list[str]):
        self.words = words
        self.possible_words = [word for word in words]

    def guess(self) -> str:
        try:
            return random.choice(self.possible_words)
        except IndexError:
            raise NoGuessesException()

    def feedback(self, guess: str, answer: list[Status]):
        placed = {index: letter for index, letter, status in zip(range(len(guess)), guess, answer) if status == Status.Placed}
        self.possible_words = [word for word in self.possible_words if all(word[index] == letter for index, letter in placed.items())]
        present_elsewhere = {index: letter for index, letter, status in zip(range(len(guess)), guess, answer) if status == Status.Present}
        self.possible_words = [word for word in self.possible_words if all(word[index] != letter for index, letter in present_elsewhere.items())]
        not_present_here = {index: letter for index, letter, status in zip(range(len(guess)), guess, answer) if status == Status.NotPresent}
        self.possible_words = [word for word in self.possible_words if all(word[index] != letter for index, letter in not_present_here.items())]
        present_counts = {}
        for letter, status in zip(guess, answer):
            present_counts.setdefault(letter, 0)
            if status in (Status.Placed, Status.Present):
                present_counts[letter] += 1
        self.possible_words = [word for word in self.possible_words if all(word.count(letter) == count for letter, count in present_counts.items())]



if __name__ == '__main__':
    with open('valid-wordle-words.txt', 'r') as f:
        words = f.read().splitlines()
    just_fix_windows_console()
    input("Please think of a five-letter word, but don't tell me what it is. Press enter when you're ready.")
    print('I will figured out what you are thinking of by guessing a word at a time.')
    print('Then you tell me which letters I got right, using ' + Status.Present.paint('this color') + ' if they are in the word and ' + Status.Placed.paint('this color') + ' if they are also in the right place.')
    print('If my guess has more than one of the same letter, and it is in your word, only color as many as appear in your word, giving priority to the most correct ones.')
    print("E.g. if you are thinking of 'allow', " + inline_tiles('ladle', calc_answer('ladle', 'allow')) + ' and ' + inline_tiles('lolly', calc_answer('lolly', 'allow')) + ' would be correct colorings for these guesses.')
    print('Now, play the game!')
    max_turns = 6
    clear_prompts = True
    random.shuffle(trash_talks)
    guessing_strategy = lambda: JonathanOlsonTree('salet.tree.hard.json')
    guesser = guessing_strategy()
    turn_number = 0
    undoing = False
    guesses = []
    answers = []
    undo_number = 0
    trash_talk_number = 0
    while turn_number < max_turns:
        turn_name = ordinal(turn_number) if turn_number < max_turns - 1 else 'last'
        if undoing:
            prompt = undoing_prompts[(undo_number - 1) % len(undoing_prompts)].format(turn_name=turn_name, guess=guess)
        else:
            try:
                guess = guesser.guess()
            except NoGuessesException:
                out_of_guesses = "Well, I'm all out of guesses."
                print(out_of_guesses)
                prompt = 'You can change a clue and let me try again by entering its number now. Otherwise, tell me the word you were thinking of: '
                word_or_number = input(prompt)
                try:
                    restart_from_turn = int(word_or_number)
                except ValueError:
                    print("That's not a word.")
                    break
                guesses = guesses[:restart_from_turn]
                answers = answers[:restart_from_turn]
                guess = guesses.pop()
                answer = answers.pop()
                undoing = True
                undo_number += 1
                print(Cursor.UP(2) + ' ' * len(out_of_guesses))
                print(' ' * (len(prompt) + len(word_or_number)))
                print(Cursor.UP(turn_number - restart_from_turn -  1 + 4), end='\r')
                guesser = guessing_strategy()
                for historical_guess, historical_answer in zip(guesses, answers):
                    guesser.feedback(historical_guess, historical_answer)
                turn_number = restart_from_turn - 1
                continue
            answer = [Status.NotPresent] * len(guess)
            trash_talk = trash_talks[trash_talk_number % len(trash_talks)]
            trash_talk_number += 1
            prompt = f"My {turn_name} guess is '{guess}'{trash_talk}"
        print(prompt)
        wizard = AnswerWizard(guess, state=answer, can_undo=turn_number > 0)
        try:
            answer = wizard.input_answer()
            record = Style.DIM + f'({turn_number + 1}) '.rjust(len(str(max_turns)) + len(' () ')) + Style.RESET_ALL + inline_tiles(guess, answer)
            if clear_prompts:
                print(Cursor.UP(1) + record + ' ' * (len(prompt) - len(guess) * record_unit_width))
            else:
                print(record)
            if all(status == Status.Placed for status in answer):
                print('Game. Over.')
                break
            guesser.feedback(guess, answer)
            guesses.append(guess)
            answers.append(answer)
            undoing = False
            turn_number += 1
        except UndoException:
            wizard.clear()
            guess = guesses.pop()
            answer = answers.pop()
            print(Cursor.UP(1) + ' ' * (len(guess) * record_unit_width + len(str(max_turns)) + len(' () ')))
            print(Cursor.UP(2) + ' ' * len(prompt), end='\r')
            undoing = True
            guesser = guessing_strategy()
            for historical_guess, historical_answer in zip(guesses, answers):
                guesser.feedback(historical_guess, historical_answer)
            undo_number += 1
            turn_number -= 1
    else:
        print("I didn't fail, you ran out of RAM.")

