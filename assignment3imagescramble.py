import cv2
import random

#asks the user for the grid size
while True:
    try:
        grid = int(input("Enter grid size (3, 4 or 5): "))

        #checks that the grid size is one of the allowed choices
        if grid in [3, 4, 5]:
            break

        print("Please enter 3, 4 or 5.")

    except ValueError:
        print("Please enter a number.")

#asks the user for the image path
image_path = input("Enter image file path: ")

#loads the image using OpenCV
image = cv2.imread(image_path)

#checks if the image was loaded properly
if image is None:
    print("Could not load the image.")
    exit()
#resize the image so it is not too large for the screen
height, width = image.shape[:2]

max_width = 800
max_height = 600

#finds how much the image needs to be resized
scale = min(max_width / width, max_height / height, 1)

new_width = int(width * scale)
new_height = int(height * scale)

image = cv2.resize(image, (new_width, new_height))

#crops the image so it can be split evenly into the grid
new_width = (new_width // grid) * grid
new_height = (new_height // grid) * grid

image = image[:new_height, :new_width]


#works out the size of each tile
tile_width = new_width // grid
tile_height = new_height // grid


#cuts the image into separate tiles
tiles = []

for y in range(grid):
    for x in range(grid):

        x1 = x * tile_width
        y1 = y * tile_height
        x2 = x1 + tile_width
        y2 = y1 + tile_height

        #copies the section of the image into a new tile
        tile = image[y1:y2, x1:x2].copy()

        tiles.append(tile)

#sets how many transformations will be used
#larger grids get more transformations
if grid == 3:
    transformation_count = 6
elif grid == 4:
    transformation_count = 12
else:
    transformation_count = 20

#stores all of the transformations before they are applied
transformations = []

#makes sure swap, rotate and flip are all used
transformations.append(("swap", None))
transformations.append(("rotate", None))
transformations.append(("flip", None))

#adds more random transformations until the required amount is reached
for i in range(transformation_count - 3):
    transformation_type = random.choice(["swap", "rotate", "flip"])
    transformations.append((transformation_type, None))

#fills in the details for each transformation
for i in range(len(transformations)):

    transformation_type = transformations[i][0]

    if transformation_type == "swap":

        #chooses two different tiles to swap
        tile1 = random.randint(0, len(tiles) - 1)
        tile2 = random.randint(0, len(tiles) - 1)

        while tile2 == tile1:
            tile2 = random.randint(0, len(tiles) - 1)

        transformations[i] = ("swap", tile1, tile2)

    elif transformation_type == "rotate":

        #chooses a tile and a random rotation
        tile_number = random.randint(0, len(tiles) - 1)
        rotation = random.choice([90, 180, 270])

        transformations[i] = ("rotate", tile_number, rotation)

    elif transformation_type == "flip":

        #chooses a tile and a random flip direction
        tile_number = random.randint(0, len(tiles) - 1)
        direction = random.choice(["horizontal", "vertical"])

        transformations[i] = ("flip", tile_number, direction)

#applies all of the transformations to the tiles
for transformation in transformations:

    if transformation[0] == "swap":

        tile1 = transformation[1]
        tile2 = transformation[2]

        #swaps the positions of the two tiles
        tiles[tile1], tiles[tile2] = tiles[tile2], tiles[tile1]

    elif transformation[0] == "rotate":
        tile_number = transformation[1]
        rotation = transformation[2]
        #rotates the tile using OpenCV
        tiles[tile_number] = cv2.rotate(
            tiles[tile_number],
            {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }[rotation]
        )
        #puts the rotated tile back to its original size
        tiles[tile_number] = cv2.resize(
            tiles[tile_number],
            (tile_width, tile_height)
        )
    elif transformation[0] == "flip":

        tile_number = transformation[1]
        direction = transformation[2]

        #flips the tile horizontally or vertically
        if direction == "horizontal":
            tiles[tile_number] = cv2.flip(tiles[tile_number], 1)
        else:
            tiles[tile_number] = cv2.flip(tiles[tile_number], 0)

#creates a blank image to put the scrambled tiles into
scrambled_image = image.copy()

#puts all of the transformed tiles back into one image
tile_number = 0

for y in range(grid):
    for x in range(grid):

        x1 = x * tile_width
        y1 = y * tile_height
        x2 = x1 + tile_width
        y2 = y1 + tile_height

        #places the current tile into its new position
        scrambled_image[y1:y2, x1:x2] = tiles[tile_number]

        tile_number += 1

#saves the finished scrambled image
cv2.imwrite("scrambled_image.png", scrambled_image)

#shows the scrambled image
cv2.imshow("Scrambled Image", scrambled_image)

print("Scrambled image saved as scrambled_image.png")
print("Press any key to close the image.")

cv2.waitKey(0)
cv2.destroyAllWindows()