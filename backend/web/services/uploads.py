from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def validate_image(upload):
    if not upload:
        return
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError('图片不能超过5MB')
    try:
        image = Image.open(upload)
        if image.format not in {'JPEG', 'PNG', 'WEBP'}:
            raise ValueError()
        if image.width * image.height > 20_000_000:
            raise ValueError()
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError('请上传有效的 JPEG、PNG 或 WebP 图片（最多2000万像素）')
    finally:
        upload.seek(0)
