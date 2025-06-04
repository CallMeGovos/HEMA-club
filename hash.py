from streamlit_authenticator.utilities.hasher import Hasher

passwords_to_hash = ['02092002']
hashed_passwords = Hasher().hash(passwords_to_hash)

print(hashed_passwords)