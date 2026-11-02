def validate_password_strength(password: str) -> None:
    if any(character.isspace() for character in password):
        raise ValueError("La contraseña no puede tener espacios.")
    if not any(character.isupper() for character in password):
        raise ValueError("La contraseña debe incluir una letra mayúscula.")
    if not any(character.islower() for character in password):
        raise ValueError("La contraseña debe incluir una letra minúscula.")
    if not any(character.isdigit() for character in password):
        raise ValueError("La contraseña debe incluir un número.")
    if not any(not character.isalnum() and not character.isspace() for character in password):
        raise ValueError("La contraseña debe incluir un símbolo (por ejemplo ! @ # $ %).")
