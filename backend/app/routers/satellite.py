from fastapi import APIRouter, Request, HTTPException, Response

router = APIRouter()

@router.get("/available")
async def get_available_layers():
    return {"layers": ["ndvi", "iron_oxide", "clay_alteration", "magnetics", "gravity", "reserve_probability"]}

@router.get("/bounds")
async def get_bounds(request: Request):
    try:
        return request.app.state.satellite_sim.get_bounds()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{layer_name}.png")
async def get_layer_png(layer_name: str, request: Request):
    try:
        if layer_name == "reserve_probability":
            png_bytes = request.app.state.reserve_model.get_reserve_png()
        else:
            png_bytes = request.app.state.satellite_sim.get_layer_png(layer_name)
        
        if not png_bytes:
            raise HTTPException(status_code=404, detail=f"Layer {layer_name} not found")
            
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
