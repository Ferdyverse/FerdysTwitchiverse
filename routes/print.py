from fastapi import APIRouter, HTTPException
import logging
from modules.schemas import PrintRequest

router = APIRouter(prefix="/print", tags=["Printer"])

logger = logging.getLogger("uvicorn.error.printer")

@router.post(
    "/",
    summary="Print data to thermal printer",
    description="Send structured data to the thermal printer for printing.",
    response_description="Returns a success message when printing is completed."
)
async def print_data(request: PrintRequest):
    """
    Endpoint to send data to the thermal printer for printing.
    Validates the printer state and sends the print elements.
    """

    printer_manager = request.app.state.printer
    obs = request.app.state.obs

    if not printer_manager.is_online():
        printer_manager.reconnect()
        if not printer_manager.is_online():
            raise HTTPException(status_code=500, detail="Printer not available")

    try:
        result = await obs.find_scene_item("Pixel 2")
        for item in result:
            await obs.set_source_visibility(item["scene"], item["id"], True)
        if request.print_as_image:
            # Print a image
            pimage = await printer_manager.create_image(elements=request.print_elements)
            printer_manager.printer.image(pimage,
                        high_density_horizontal=True,
                        high_density_vertical=True,
                        impl="bitImageColumn",
                        fragment_height=960,
                        center=True)
        else:
            for element in request.print_elements:
                if await printer_manager.print_element(element):
                    printer_manager.newline(1)
        printer_manager.cut_paper(partial=True)
        return {"status": "success", "message": "Print done!"}
    except Exception as e:
        logger.error(f"Error during printing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
