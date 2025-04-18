from googletrans import Translator


def do_translation(text:str , target_lang:str) -> str :

    translator = Translator()

    # Translate text to Arabic
    result = translator.translate(text, dest=target_lang)
    return result.text  