#!/bin/bash
python . --mode=assume --strategy=null_action
python . --mode=single --strategy=drawio_draw

python . --mode=assume --strategy=png_draw
python . --mode=single --strategy=png_draw