def remove_old_photo(photo):
    if photo and photo.name != 'user/photos/default.png':
        if photo.storage.exists(photo.name):
            photo.storage.delete(photo.name)
