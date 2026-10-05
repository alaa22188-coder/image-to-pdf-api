import io
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse
from PIL import Image

app = FastAPI(title="Image to PDF Converter API")


def convert_image_to_rgb(img: Image.Image) -> Image.Image:
    """
    Converts any image mode (RGBA, LA, P, Grayscale) to RGB format for PDF compatibility.
    Handles transparency in PNG/WEBP images by applying a white background.
    """
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        return background
    elif img.mode != "RGB":
        return img.convert("RGB")
    return img


@app.post("/convert-to-pdf", summary="Convert images to a single PDF")
async def convert_to_pdf(
    files: List[UploadFile] = File(
        ..., description="Upload one or multiple images to convert into a single PDF"
    ),
    filename: str = Query("converted.pdf", description="Output PDF filename"),
):
    if not files:
        raise HTTPException(
            status_code=400, detail="Please upload at least one image file."
        )

    rgb_images: List[Image.Image] = []

    for file in files:
        try:
            contents = await file.read()
            img = Image.open(io.BytesIO(contents))
            img.load()
            
            rgb_img = convert_image_to_rgb(img)
            rgb_images.append(rgb_img)

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process file '{file.filename}'. Ensure it is a valid image format. Error: {str(e)}",
            )

    if not rgb_images:
        raise HTTPException(
            status_code=400, detail="No valid images were processed."
        )

    # Save converted RGB images into an in-memory PDF buffer
    pdf_buffer = io.BytesIO()
    first_image = rgb_images[0]
    remaining_images = rgb_images[1:]

    first_image.save(
        pdf_buffer,
        format="PDF",
        save_all=True,
        append_images=remaining_images,
    )

    pdf_buffer.seek(0)

    # Ensure output file extension is .pdf
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )