from livekit.agents import stt, utils
print("STT Capabilities:")
print([attr for attr in dir(stt) if "Cap" in attr])
print("AudioBuffer attributes:")
print(dir(utils.AudioBuffer))
