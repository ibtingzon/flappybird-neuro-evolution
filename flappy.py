from itertools import cycle
import random
import sys
import pygame
from pygame.locals import *

import numpy as np
import copy
from player import Player
import genetic
import time
import gc

NGEN = 1000
SIZE = 50
GEN = 0

FPS = 30
SCREENWIDTH  = 288
SCREENHEIGHT = 512
# amount by which base can maximum shift to left
PIPEGAPSIZE  = 100 # gap between upper and lower part of pipe
BASEY        = SCREENHEIGHT * 0.79
# image, sound and hitmask  dicts
IMAGES, SOUNDS, HITMASKS = {}, {}, {}

# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # red bird
    (
        'assets/sprites/redbird-upflap.png',
        'assets/sprites/redbird-midflap.png',
        'assets/sprites/redbird-downflap.png',
    ),
    # blue bird
    (
        # amount by which base can maximum shift to left
        'assets/sprites/bluebird-upflap.png',
        'assets/sprites/bluebird-midflap.png',
        'assets/sprites/bluebird-downflap.png',
    ),
    # yellow bird
    (
        'assets/sprites/yellowbird-upflap.png',
        'assets/sprites/yellowbird-midflap.png',
        'assets/sprites/yellowbird-downflap.png',
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    'assets/sprites/background-day.png',
    'assets/sprites/background-night.png',
)

# list of pipes
PIPES_LIST = (
    'assets/sprites/pipe-green.png',
    'assets/sprites/pipe-red.png',
)


try:
    xrange
except NameError:
    xrange = range

def main():
    global SCREEN, FPSCLOCK, GEN

    population = []
    for i in range(SIZE + int(SIZE/2)):
        player = Player()
        #player.loadModel(GEN, i)
        population.append(player)

    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
    pygame.display.set_caption('Flappy Bird')

    # numbers sprites for score display
    IMAGES['numbers'] = (
        pygame.image.load('assets/sprites/0.png').convert_alpha(),
        pygame.image.load('assets/sprites/1.png').convert_alpha(),
        pygame.image.load('assets/sprites/2.png').convert_alpha(),
        pygame.image.load('assets/sprites/3.png').convert_alpha(),
        pygame.image.load('assets/sprites/4.png').convert_alpha(),
        pygame.image.load('assets/sprites/5.png').convert_alpha(),
        pygame.image.load('assets/sprites/6.png').convert_alpha(),
        pygame.image.load('assets/sprites/7.png').convert_alpha(),
        pygame.image.load('assets/sprites/8.png').convert_alpha(),
        pygame.image.load('assets/sprites/9.png').convert_alpha()
    )

    # game over sprite
    IMAGES['gameover'] = pygame.image.load('assets/sprites/gameover.png').convert_alpha()
    # message sprite for welcome screen
    IMAGES['message'] = pygame.image.load('assets/sprites/message.png').convert_alpha()
    # base (ground) sprite
    IMAGES['base'] = pygame.image.load('assets/sprites/base.png').convert_alpha()

    # sounds
    if 'win' in sys.platform:
        soundExt = '.wav'
    else:
        soundExt = '.ogg'

    SOUNDS['die']    = pygame.mixer.Sound('assets/audio/die' + soundExt)
    SOUNDS['hit']    = pygame.mixer.Sound('assets/audio/hit' + soundExt)
    SOUNDS['point']  = pygame.mixer.Sound('assets/audio/point' + soundExt)
    SOUNDS['swoosh'] = pygame.mixer.Sound('assets/audio/swoosh' + soundExt)
    SOUNDS['wing']   = pygame.mixer.Sound('assets/audio/wing' + soundExt)

    while True:
        # select random background sprites
        randBg = random.randint(0, len(BACKGROUNDS_LIST) - 1)
        IMAGES['background'] = pygame.image.load(BACKGROUNDS_LIST[randBg]).convert()

        # select random player sprites
        randPlayer = random.randint(0, len(PLAYERS_LIST) - 1)
        IMAGES['player'] = (
            pygame.image.load(PLAYERS_LIST[randPlayer][0]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][1]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][2]).convert_alpha(),
        )

        # select random pipe sprites
        pipeindex = random.randint(0, len(PIPES_LIST) - 1)
        IMAGES['pipe'] = (
            pygame.transform.rotate(
                pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(), 180),
            pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(),
        )

        # hismask for pipes
        HITMASKS['pipe'] = (
            getHitmask(IMAGES['pipe'][0]),
            getHitmask(IMAGES['pipe'][1]),
        )

        # hitmask for player
        HITMASKS['player'] = (
            getHitmask(IMAGES['player'][0]),
            getHitmask(IMAGES['player'][1]),
            getHitmask(IMAGES['player'][2]),
        )

        #showWelcomeAnimation(population)
        crashInfo = mainGame(population)
        population = showGameOverScreen(crashInfo)

def mainGame(population):
    basex = 0
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    # get 2 new pipes to add to upperPipes lowerPipes list
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()

    # list of upper pipes
    upperPipes = [
        {'x': SCREENWIDTH + 200, 'y': newPipe1[0]['y']},
        {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[0]['y']},
    ]

    # list of lowerpipe
    lowerPipes = [
        {'x': SCREENWIDTH + 200, 'y': newPipe1[1]['y']},
        {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[1]['y']},
    ]

    pipeVelX = -4

    # player velocity, max velocity, downward accleration, accleration on flap
    for player in population:
        player.score = 0
        player.dist = 0
        player.active = True
        player.fitness = -1000

        player.playerVelY    =  -9   # player's velocity along Y, default same as playerFlapped
        player.playerMaxVelY =  10   # max vel along Y, max descend speed
        player.playerMinVelY =  -8   # min vel along Y, max ascend speed
        player.playerAccY    =   1   # players downward accleration
        player.playerFlapAcc =  -9   # players speed on flapping
        player.playerFlapped = False # True when player flaps
        player.loopIter = 0

        player.playerIndex = 0
        player.playerShmVals = {'val': 0, 'dir': 1}
        player.playerIndexGen = cycle([0, 1, 2, 1])
        player.playerx, player.playery = int(SCREENWIDTH * 0.2), int((SCREENHEIGHT - IMAGES['player'][0].get_height()) / 2)

    pipes = 1
    next_pipe_x = lowerPipes[0]['x']
    next_pipe_y = lowerPipes[0]['y'] 
    scores = [0]

    while True:
        active_players = []
        for player in population:
            if player.active: 
                player.dist += 1
                active_players.append(player)

        if len(active_players) == 0:
            info = {
                'players': population,
                'lowerPipes': lowerPipes,
            }
            return info

        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()

        for player in population:
            if player.active:
                dist1 = next_pipe_x/SCREENWIDTH
                dist2 = (player.playery - next_pipe_y)/SCREENHEIGHT

                if player.predict(dist1, dist2) == 1:
                    if player.playery > -2 * IMAGES['player'][0].get_height():
                        player.playerVelY = player.playerFlapAcc
                        player.playerFlapped = True
                        #SOUNDS['wing'].play()

                # check for crash here
                crashTest = checkCrash({'x': player.playerx, 'y': player.playery, 
                                        'index': player.playerIndex}, upperPipes, lowerPipes)
                if crashTest[0] or player.playery < 0:
                    if crashTest[1] or player.playery < 0: 
                        player.dist = player.dist/10
                    player.active = False

                if player.active:
                    playerMidPos = player.playerx + IMAGES['player'][0].get_width() / 2
                    pipe_id = 0
                    for pipe in upperPipes:
                        pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2
                        if playerMidPos > pipe['x'] + IMAGES['pipe'][0].get_width():
                            next_pipe_x = lowerPipes[pipe_id+1]['x']
                            next_pipe_y = lowerPipes[pipe_id+1]['y']
                            pipe_id += 1
                        if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                            if player.score < pipes:
                                player.score += 1
                                SOUNDS['point'].play()

                    # playerIndex basex change
                    if (player.loopIter + 1) % 3 == 0:
                        player.playerIndex = next(player.playerIndexGen)
                    player.loopIter = (player.loopIter + 1) % 30

                    # player's movement
                    if player.playerVelY < player.playerMaxVelY and not player.playerFlapped:
                        player.playerVelY += player.playerAccY
                    if player.playerFlapped:
                        player.playerFlapped = False
                    playerHeight = IMAGES['player'][player.playerIndex].get_height()
                    player.playery += min(player.playerVelY, BASEY - player.playery - playerHeight)
                    scores.append(player.score)

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe['x'] += pipeVelX
            lPipe['x'] += pipeVelX
        next_pipe_x += pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < upperPipes[0]['x'] < 5:
            pipes += 1
            newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if upperPipes[0]['x'] < -IMAGES['pipe'][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        # draw sprites
        SCREEN.blit(IMAGES['background'], (0,0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        basex = -((-basex + 100) % baseShift)
        SCREEN.blit(IMAGES['base'], (basex, BASEY))

        for player in population:
            if player.active: 
                SCREEN.blit(IMAGES['player'][player.playerIndex], (player.playerx, player.playery))

        # print score so player overlaps the score                
        showScore(max(scores))

        pygame.display.update()
        FPSCLOCK.tick(FPS)


def showGameOverScreen(crashInfo):
    global GEN

    print("\nGeneration " + str(GEN))
    lowerpipe = crashInfo['lowerPipes']
    players = crashInfo['players']

    for i, player in enumerate(players):
        player.setFitness()
        print(i, " Fitness: ", player.score*100, player.dist, player.fitness)

    elite_players = []
    while len(elite_players) < SIZE:
        best_player = genetic.getBest(list(set(players) - set(elite_players)))
        elite_players.append(best_player)

    print("\n\nEvolving new generation...")
    new_weights = []
    while len(new_weights) < SIZE:
        if len(new_weights) % 5 == 0:
            print(str(len(new_weights)) + ' of ' + str(SIZE)  + ' done...')

        parents = genetic.tournament(elite_players[:int(SIZE/2)], 2, 3)
        parent1 = parents[0].model.get_weights()
        parent2 = parents[1].model.get_weights()

        if random.random() <= 0.85:
            child1, child2 = genetic.crossover(parent1, parent2)
        else:
            child1 = copy.deepcopy(parent1) if parents[0].fitness > parents[1].fitness else copy.deepcopy(parent2)
        if random.random() > 0.85 or random.random() < 0.7:
            child1 = genetic.mutate(child1)
        new_weights.append(child1)

    print(str(len(new_weights)) + ' of ' + str(SIZE)  + ' done...')

    for player in elite_players[:int(SIZE/2)]:
        new_weights.append(player.model.get_weights())

    population = players[:int(SIZE)] + elite_players[:int(SIZE/2)]
    for player, weights in zip(population, new_weights):
        player.model.set_weights(weights)

    index = 0
    if GEN % 10 == 0:
        print("Saving new models")
        for index, player in enumerate(population):
            player.id = index
            player.saveModel(GEN)

    gc.collect()

    GEN = GEN + 1
    if GEN < NGEN:
        return population

def playerShm(playerShm):
    """oscillates the value of playerShm['val'] between 8 and -8"""
    if abs(playerShm['val']) == 8:
        playerShm['dir'] *= -1

    if playerShm['dir'] == 1:
         playerShm['val'] += 1
    else:
        playerShm['val'] -= 1
    return playerShm

def getRandomPipe():
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = SCREENWIDTH + 10

    return [
        {'x': pipeX, 'y': gapY - pipeHeight},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE}, # lower pipe
    ]


def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
        Xoffset += IMAGES['numbers'][digit].get_width()


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][0].get_width()
    player['h'] = IMAGES['player'][0].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return [True, True]
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])
        pipeW = IMAGES['pipe'][0].get_width()
        pipeH = IMAGES['pipe'][0].get_height()

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y
    for x in xrange(rect.width):
        for y in xrange(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in xrange(image.get_width()):
        mask.append([])
        for y in xrange(image.get_height()):
            mask[x].append(bool(image.get_at((x,y))[3]))
    return mask

if __name__ == '__main__':
    main()
