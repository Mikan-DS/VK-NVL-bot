# -*- coding: utf-8 -*-

from threading import Thread
from time import sleep

import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from config import *

vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()
longpool = VkLongPoll(vk_session)


###############################################################################
# Init main elements (mpy actions)
###############################################################################
class Say:
    """
    Say(what, who=None, name=None) => action

    what - character speech
    who - character name
    name - is not working now


    """

    def __init__(self, what, who=None, name=None):
        self.text = what
        self.who = who
        self.name = name

    def __call__(self, player):
        """send message with speech"""
        text = (self.who + ":\n\n       ") if self.who else ""
        text += self.text
        vk.messages.send(user_id=player.id, message=text, random_id=0)
        sleep(len(self.text) / 50)  # speed of sending current speech


class Show:
    """
    Show(src) => action

    src (str) - vk image/video/audio url, that contains
    type-user_id-source_id. example "photo-194303024_457239055"

    """

    def __init__(self, src):
        self.source = src

    def __call__(self, player):
        """send message with attachment"""
        vk.messages.send(user_id=player.id, attachment=self.source, random_id=0)


class Menu:
    """
    Menu(buttons) => action

    buttons (dict) - {name_1: label_1, name_2: label_2, ... }

        name - label of button
        label - label to which game will jump


    !This action must be last in the label

    """

    def __init__(self, buttons):
        """Init keyboard"""
        self.questions = buttons

        self.keyboard = {
            "one_time": True,
            "buttons": [[button(i), ] for i in buttons
                        ]
        }
        self.keyboard = json.dumps(self.keyboard, ensure_ascii=False).encode('utf-8')
        self.keyboard = str(self.keyboard.decode('utf-8'))

    def __call__(self, player):
        """send message with menu buttons"""
        vk_session.method('messages.send',
                          {'user_id': player.id, 'message': "Выбор:", 'random_id': 0, 'keyboard': self.keyboard})

        player.question = self.questions  # using for catching choices


class Assign:
    """
    Assign(value, dst) => action

    value - name of value that must be changed
    dst (function) - function (lambda) that would be executed,
    whose return value will be the new value for "value-name"

    function must take one argument, example

            lambda player: player.values["yuri_love"] + 1

    """

    def __init__(self, value, dst):
        self.value = value
        self.dst = dst

    def __call__(self, player):
        """assign value"""
        player.values[self.value] = self.dst(player)


class If:
    """
    If(condition, action, else_action) => action

    condition (function) - function (lambda) that would be executed,
    whose return value must be bool (using for python "if")
        function must take one argument, example

            lambda player: 3 > 2

    action - can be label name, or mpy action. would be executed
    if condition return value be True
    else_action - can be label name, mpy action or None. would be executed
    if condition return value be False, or pass if else_action is None


    """

    def __init__(self, condition, action, else_action=None):
        self.condition = condition
        self.action = action
        self.else_action = else_action

    def __call__(self, player):
        """
        Check condition and execute

        r - if action have returned value, it will return it to the main game Thread
        for example if action is Jump().

        if action is label name, it will execute it and after continue executing current
        label. So, if you need to jump to another label use Jump() action


        """

        r = None

        if self.condition(player):
            if isinstance(self.action, str):
                player.jump(self.action)
            else:
                r = self.action(player)
        elif self.else_action:
            if isinstance(self.else_action, str):
                player.jump(self.else_action)
            else:
                r = self.else_action(player)

        return r


class Jump:
    """
    Jump(label) => action

    label - label name to which game must jump

    """

    def __init__(self, label):
        self.label = label

    def __call__(self, player):
        """stop current label, and jump to new"""
        return self.label


class Game:
    """
    Main manager for each player
    """

    def __init__(self, user, labels):
        self.id = user

        self.clabel = "start"  # current label
        self.cline = 0  # current line of clabel

        self.values = {"book": False}  # default value, in future must be changed from the outside

        self.question = {}  # help catch player's choices
        self.labels = labels  # in future would use global value
        Thread(target=self.jump, args=["start"]).start()

    def jump(self, label, line=0):

        self.clabel = label  # current label
        self.cline = line  # current line of clabel

        print(label + " : " + str(self.id))  # need for log
        j = None  # if there is any returning value - break executing and jump to new label "j"

        for self.cline, action in enumerate(self.labels[label][line:]):
            try:
                j = action(self)
            except Exception as e:
                print(f"Mistake occurs in {self.clabel} line {self.cline}\
                        \nPlayer id: {self.id}\
                        \nTypeError: {e}")

                GAMES.pop(self.id)  # remove player, so he can start again
                break
            print(self.cline)  # need for log
            sleep(0.4)
            if j:
                break
        if j:
            self.jump(j)


def button(text):
    """Help function to create button"""
    return {
        "action": {
            "type": "callback",
            "payload": "{}",
            "label": f"{text}"
        },
    }


###############################################################################
# load story (for now, story is located inside the engine)
###############################################################################

s = "Сильвия"
m = "Я"
Story = {
    "start": [
        Show("photo-199752462_457239026"),
        Say("Только когда я услышал шорох ног и сумок, я понял, что лекция кончилась."),
        Say("Лекции профессора Эйлин обычно интересные, но сегодня я просто не смог сконцентрироваться."),
        Say("У меня было много разных мыслей в голове… и все эти мысли кульминировались вопросом."),
        Say("Вопросом, который я давно хотел задать определённому человеку."),
        Show("photo-199752462_457239025"),
        Say("Когда мы вышли из университета, я тут же заметил её."),
        Show("photo-199752462_457239034"),
        Say(
            "Я знал Сильви ещё с тех лет, когда мы были детьми."
            " У неё большое сердце и она всегда была мне хорошим другом."),
        Say("Но в последнее время… Я почувствовал, что мне хочется чего-то большего."),
        Say("Большего, чем просто разговоры. Больше, чем просто ходить домой вместе с концом наших занятий."),
        Say("Как только мы встретились взглядами, я решил..."),
        Menu({"Спросить её сейчас": "rightaway", "Подождать другого момента...": "later"})
    ],
    "rightaway": [
        Show("photo-199752462_457239035"),
        Say("Привет! Как тебе урок?", s),
        Say("Хорошо…", m),
        Say("Я не мог собраться и признать, что весь он сначала влетел в одно ухо, а затем вылетел в другом.", m),
        Say("Ты сейчас идёшь домой? Хочешь пройтись вместе со мной?", m),
        Say("Конечно!", m),
        Show("photo-199752462_457239027"),
        Say("Через некоторое время мы дошли до луга, начинавшегося за нашим родным городом, в котором мы жили."),
        Say("Здесь живописный вид, к которому я уже привык. Осень здесь была особенно прекрасна."),
        Say("Когда мы были детьми, мы много играли на этих лугах. Так много здесь воспоминаний."),
        Say("Эй… Эмм…", m),
        Show("photo-199752462_457239035"),
        Say(
            "Она повернулась ко мне и улыбнулась. "
            "Она выглядела настолько дружелюбной, что вся моя нервозность улетучилась."),
        Say("Я спрошу её..!", "💭"),
        Say("Эммм… Хотела бы ты…", m),
        Say("Хотела бы ты стать художницей моей визуальной новеллы?", m),
        Show("photo-199752462_457239036"),
        Say("Тишина."),
        Say("Она выглядела столь шокированной, что я начал бояться худшего. Но затем…"),
        Show("photo-199752462_457239036"),
        Say("Конечно, но что такое \"визуальная новелла\"?", s),
        Menu({"Это видеоигра": "game", "Это интерактивная книга": "book"})

    ],
    "game": [
        Say("Это вроде видеоигры, в которую ты можешь играть на своём компьютере или консоли.", m),
        Say("Ну или, если разработчики знают толк в извращениях - то делают бота вк.", m),
        Say("В визуальных новеллах рассказывается история с картинками и музыкой.", m),
        Say("Иногда ты также можешь делать выборы, которые влияют на конец истории.", m),
        Say("То есть это как те книги-игры?", s),
        Say("Точно! У меня есть много разных идей, которые, по-моему, могут сработать.", m),
        Say("И я думал, что ты могла бы помочь мне… так как я знаю, как тебе нравится рисовать.", m),
        Say("Мне одному будет трудно делать визуальную новеллу.", m),
        Show("photo-199752462_457239034"),
        Say("Ну конечно! Я могу попытаться. Надеюсь, я тебя не разочарую.", m),
        Say("Сильви, ты же знаешь, ты никогда не сможешь меня разочаровать.", m),
        Jump("marry")
    ],
    "book": [
        Assign("book", lambda player: True),
        Say("Это как интерактивная книга, которую ты можешь читать на компьютере или консоли.", m),
        Show("photo-199752462_457239036"),
        Say("Интерактивная?", s),
        Say("Ты можешь делать выборы, которые ведут к различным событиям и концовкам истории.", m),
        Say("А когда в дело вступает \"визуальная\" часть?", s),
        Say(
            "В визуальных новеллах есть картинки и даже музыка, звуковые эффекты, "
            "и иногда озвучка, которая идёт наравне с текстом.",
            m),
        Say(
            "Ясно! Это определённо кажется весёлым."
            " Если честно, я раньше делала веб-комиксы, так что у меня есть много идей.",
            s),
        Say("Это отлично! Так… ты хочешь работать со мной в качестве художницы?", m),
        Say("Хочу!", m),
        Jump("marry")

    ],
    "marry": [
        Say("...\n\n\n...\n\n\n"),
        Say("И так мы стали командой разработки визуальных новелл."),
        Say("За долгие годы мы сделали много игр, получив при этом много веселья."),
        If(lambda player: player.values["book"],
           Say("Наша первая игра была основана на одной из идей Сильви, но затем я начал давать и свои идеи.")),
        Say("Мы по очереди придумывали истории и персонажей, и поддерживали друг друга в разработке отличных игр!"),
        Say("И в один день…"),
        Show("photo-199752462_457239030"),
        Say("Эй…", s),
        Say("Да?", s),
        Show("photo-199752462_457239029"),
        Say("Ты женишься на мне?", s),
        Say("Что? С чего это ты вдруг?", m),
        Show("photo-199752462_457239032"),
        Say("Да ладно тебе, сколько мы уже встречаемся?", s),
        Say("Некоторое время…", m),
        Show("photo-199752462_457239031"),
        Say("Последнюю пару лет мы делаем визуальные новеллы и проводим время вместе, помогаем друг другу…", s),
        Say(
            "Я узнала тебя и заботилась о тебе больше, чем о ком-либо ещё."
            " И я думаю, что ты чувствуешь то же самое, верно?",
            s),
        Say("Сильви…", m),
        Show("photo-199752462_457239029"),
        Say("Но я знаю, что ты нерешительный. Если бы я сдержалась, кто знает, когда бы ты сделал мне предложение?", s),
        Show("photo-199752462_457239030"),
        Say("Так ты женишься на мне?", s),
        Say("Конечно, я женюсь! На самом деле я действительно хотел сделать тебе предложение, клянусь!", m),
        Say("Я знаю, знаю.", s),
        Say("Думаю… Я просто слишком волновался о времени. Я хотел задать правильный вопрос в правильное время.", m),
        Show("photo-199752462_457239029"),
        Say("Ты слишком сильно волнуешься. Если бы это была визуальная новелла, то я бы выбрала придать тебе смелости!",
            s),
        Say("...\n\n\n\n...\n\n\n\n"),
        Show("photo-199752462_457239028"),
        Say("Мы поженились вскоре после этого."),
        Say("Наш дуэт разработки жил и после нашей свадьбы… и я изо всех сил старался стать решительнее."),
        Say("Вместе мы жили долго и счастливо."),
        Say("=============\n\n\n\n\n\n\n\n\nХорошая концовка"),
        Menu({"Начать с начала": "start"})

    ],
    "later": [
        Say("У меня не было сил собраться и спросить её в эту секунду. Сглотнув, я решил спросить её позже."),
        Show("photo-199752462_457239028"),
        Say("Но я был нерешителен."),
        Say("Я не спросил у неё в тот день и не смог спросить больше никогда."),
        Say("Полагаю, теперь я никогда не узнаю ответ на мой вопрос…"),
        Say("=============\n\n\n\n\n\n\n\n\nПлохая концовка"),
        Menu({"Начать с начала": "start"})
    ]
}


###############################################################################
# vk side
###############################################################################


def STAY_ALIVE():
    """waking up server"""
    while True:
        vk.messages.send(user_id=559825295, message="5 min more", random_id=0)
        sleep(600)


GAMES = {}
Thread(target=STAY_ALIVE).start()

for event in longpool.listen():

    if event.type == VkEventType.MESSAGE_NEW and event.to_me:

        user_id = event.user_id
        if user_id in GAMES:
            if event.text in GAMES[user_id].question:
                # GAMES[user_id].jump(GAMES[user_id].question[event.text])
                Thread(target=GAMES[user_id].jump, args=[GAMES[user_id].question[event.text]]).start()
        else:
            GAMES[user_id] = Game(user_id, Story)

print(GAMES)
