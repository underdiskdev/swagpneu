import discord
import aiohttp
import uuid
import os
import shutil
import textwrap
import configparser

from pytube import YouTube
import moviepy.editor as mpy
import gizeh as gz
from math import pi
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

client = discord.Client()

prefix = '%'
lasturl = ''
ext = ''
unique_id = ''

shutil.rmtree(os.getcwd() + "/resource", ignore_errors=True)
os.mkdir(os.getcwd() + "/resource")

config = configparser.ConfigParser()
config.read("config.ini")
token = config["PRIVATE"]["Token"]

def change_lasturl(filename, url):
	global lasturl
	global ext
	global unique_id

	lasturl = url
	if filename.endswith('.jpg') or filename.endswith('.jpeg'):
		ext = '.jpg'
	elif filename.endswith('.png'):
		ext = '.png'
	elif filename.endswith('.mp4'):
		ext = '.mp4'
	unique_id = uuid.uuid4()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
	if len(message.attachments) != 0:
		change_lasturl(message.attachments[0].filename, message.attachments[0].url)

	tokens = message.content.split()

	if len(tokens) != 0 and tokens[0][0] == prefix:
		tokens[0] = tokens[0][1:]
		print(tokens)
		if tokens[0] == 'help':
			await message.channel.send(
			prefix + 'help - display this message\n' +
			prefix + 'edit [params] - edit photo or video')

		if len(tokens) == 0:
			await message.channel.send("No command specified. Returning untouched image")

		if len(message.attachments) != 0:
			change_lasturl(message.attachments[0].filename, message.attachments[0].url)
		if lasturl != '':
			await message.channel.send("Working on it... :gear:")

			path = os.getcwd() + "/resource/{" + str(unique_id) + "[" + str(hash(message.channel)) + "]}"
			os.mkdir(path)
			async with aiohttp.ClientSession() as session:
				async with session.get(lasturl) as data:
					if data.status == 200:
						file = open(path + "/data" + ext, "xb")
						file.write(await data.read())	
						file.close()

			err = edit_image(path + "/data" + ext, tokens.pop(0), tokens)
			if err != "OK" and err != "OKVID":
				await message.channel.send("Error: " + err)
			elif err == "OK":
				await message.channel.send(file=discord.File(path + "/data" + ext))
			elif err == "OKVID":
				await message.channel.send(file=discord.File(path + "/data" + ext + ".mp4"))
			#delete all files in ./resources
			shutil.rmtree(path, ignore_errors=True)
		else:
			await message.channel.send("No input file")


def saturate_img(path, value):
	try:
		value = float(value)
	except Exception as e:
		return str(e)

	image = Image.open(path)
	image = image.convert("RGB")
	converter = ImageEnhance.Color(image)
	try:
		image2 = converter.enhance(value)
		image2.save(path, "PNG")
	except Exception as e:
		return str(e)
	return "OK"

def meme_img(path, line):
	try:
		line = str(line)
	except Exception as e:
		return str(e)

	tokens = line.split('\\n')

	if len(tokens) == 0:
		return "No tokens"
	
	print(tokens)

	image = Image.open(path)
	image = image.convert("RGB")

	width, height = image.size

	d = ImageDraw.Draw(image)

	coef = int((width*2)/len(tokens[0]))
	if coef > height/5:
		coef = int(height/5)

	fnt = ImageFont.truetype(os.getcwd() + "/fonts/unicode.impact.ttf", size=coef)

	text_width, text_height = d.textsize(tokens[0].upper(), font=fnt, stroke_width=int(coef/13))

	pos_x = width/2 - text_width/2
	pos_y = text_height * 0.08
	d.text((pos_x,pos_y), tokens[0].upper(), font=fnt, fill=(255,255,255,255), stroke_width=int(coef/13), stroke_fill='black')

	image.save(path, "PNG")
	return "OK"

def jpeg_img(path, qual):
	try:
		qual = int(qual)
	except Exception as e:
		return str(e)

	image = Image.open(path)
	image = image.convert("RGB")
	image.save(path, "JPEG", quality=qual)
	return "OK"

def video_img(path, length):

	try:
		length = float(length)

		img = mpy.ImageClip(path).set_duration(length).write_videofile(path + ".mp4", fps=10)

	except Exception as e:
		return str(e)

	return "OKVID"

def video_sound(path, url, offset):
	try:
		offset = float(offset)
		yt = YouTube(url)
		stream = yt.streams.filter(only_audio=True).first().download(path + "-AUDIO", filename="media")

		os.rename(path, path + "ori.mp4")
		
		audio = mpy.AudioFileClip(path + "-AUDIO/media.mp4")
		video = mpy.VideoFileClip(path + "ori.mp4")
		audio = audio.subclip(offset, offset+video.duration)

		video.set_audio(audio)
		video.write_videofile(path, temp_audiofile="temp-audio.m4a", remove_temp=False, codec="libx264", audio_codec="aac")

	except Exception as e:
		return str(e)
	
	return "OK"

def edit_image(path, command, args):
	global ext
	global prefix

	argslen = len(args)
	if ext == '.jpg' or ext == '.png':
		if command == 'video':
			if argslen == 1:
				return video_img(path, args[0])
			else:
				return prefix + "video <length(sec):number>"
		if command == 'saturate':
			if argslen >= 1:
				return saturate_img(path, args[0])
			else:
				return prefix + "saturate <value:number>"
		elif command == 'meme':
			if argslen >= 1:
				return meme_img(path, ' '.join(args))
			else:
				return prefix + "meme <text:string> (use '\\n' to separate top and bottom text)"
		elif command == 'jpeg':
			qual = 0
			if argslen >= 1:
				qual = args[0]
			return jpeg_img(path, qual)
		else:
			return "Unknown command for images"
	elif ext == '.mp4':
		if command == "sound":
			if argslen != 2:
				return prefix + "sound <url(youtube):string> <offset(sec):number"
			else:
				return video_sound(path, args[0], args[1])
		else:
			return "Unknown command for videos"
	else:
		return "Unknown file format"

client.run(token)