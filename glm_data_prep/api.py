"""FastAPI backend for GLM Data Preparation Tool."""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
from pathlib import Path

from glm_data_prep.schemas import (
    StudyPeriodConfig,
    PremiumColumnMapping,
    ClaimsColumnMapping,
    ProcessingResponse,
    OneWayAnalysisRequest,
    TwoWayAnalysisRequest,
    GLMSpecification,
    GLMResults,
)
from glm_data_prep.models.premium import PremiumProcessor
from glm_data_prep.models.claims import ClaimsProcessor
from glm_data_prep.models.large_loss import LargeLossProcessor
from glm_data_prep.models.consolidation import DataConsolidator
from glm_data_prep.models.transformations import VariableTransformer
from glm_data_prep.models.analysis import (
    AnalysisDatasetBuilder,
    OneWayAnalyzer,
    TwoWayAnalyzer,
)
from glm_data_prep.glm.fitting import GLMFitter
from glm_data_prep.glm.diagnostics import GLMDiagnostics

app = FastAPI(
    title="GLM Data Preparation Tool",
    description="High-performance GLM data preparation for insurance actuarial analysis",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
state = {
    "study_config": None,
    "premium_data": None,
    "claims_data": None,
    "consolidated_data": None,
    "analysis_data": None,
}


@app.on_event("startup")
async def startup():
    """Initialize app."""
    print("GLM Data Preparation Tool API started")


@app.post("/api/config/study-period")
async def configure_study_period(config: StudyPeriodConfig):
    """
    Configure study period and analysis parameters.

    Args:
        config: Study period configuration

    Returns:
        Success response
    """
    if config.end_date < config.start_date:
        raise HTTPException(status_code=400, detail="End date must be >= start date")

    state["study_config"] = config.dict()

    return {
        "success": True,
        "message": f"Study period configured: {config.start_date} to {config.end_date}",
        "config": state["study_config"],
    }


@app.post("/api/data/premium/upload")
async def upload_premium_data(
    file: UploadFile = File(...),
    column_mapping: str = "",
):
    """
    Upload and process premium data.

    Args:
        file: CSV file upload
        column_mapping: JSON string with column mappings

    Returns:
        Processing results
    """
    if not state["study_config"]:
        raise HTTPException(
            status_code=400, detail="Configure study period first"
        )

    try:
        # Save temporary file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        config = state["study_config"]
        processor = PremiumProcessor(
            study_start=config["start_date"],
            study_end=config["end_date"],
            premium_type=config["premium_type"],
            accident_year_split=config["accident_year_split"],
        )

        # TODO: Parse column_mapping from request
        # For now, use placeholder mappings
        premium1, log = processor.process(
            file_path=tmp_path,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            date_format="dmy",
        )

        state["premium_data"] = premium1

        return {
            "success": True,
            "record_count": len(premium1),
            "validation_log": log.summary(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/data/claims/upload")
async def upload_claims_data(file: UploadFile = File(...)):
    """
    Upload and process claims data.

    Args:
        file: CSV file upload

    Returns:
        Processing results
    """
    if not state["study_config"]:
        raise HTTPException(
            status_code=400, detail="Configure study period first"
        )

    try:
        # Save temporary file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        config = state["study_config"]
        processor = ClaimsProcessor(
            study_start=config["start_date"],
            study_end=config["end_date"],
        )

        claims1, log = processor.process(
            file_path=tmp_path,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        state["claims_data"] = claims1

        return {
            "success": True,
            "record_count": len(claims1),
            "validation_log": log.summary(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/analysis/consolidate")
async def consolidate_data():
    """
    Consolidate premium and claims data.

    Returns:
        Consolidation results
    """
    if not state["premium_data"] is not None or state["claims_data"] is None:
        raise HTTPException(
            status_code=400,
            detail="Upload premium and claims data first",
        )

    try:
        config = state["study_config"]
        consolidator = DataConsolidator(
            accident_year_split=config["accident_year_split"]
        )

        consolidated, orphans = consolidator.consolidate(
            premium=state["premium_data"],
            claims=state["claims_data"],
        )

        state["consolidated_data"] = consolidated

        return {
            "success": True,
            "consolidated_records": len(consolidated),
            "orphan_summary": consolidator.get_orphan_summary(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analysis/one-way")
async def perform_one_way_analysis(request: OneWayAnalysisRequest):
    """
    Perform one-way analysis.

    Args:
        request: One-way analysis parameters

    Returns:
        Analysis results
    """
    if state["analysis_data"] is None:
        raise HTTPException(
            status_code=400,
            detail="Create analysis dataset first",
        )

    try:
        config = state["study_config"]
        analyzer = OneWayAnalyzer(
            state["analysis_data"],
            premium_type=config["premium_type"],
        )

        results = analyzer.analyze(request.variable)

        return {
            "success": True,
            "claim_type": request.claim_type,
            "variable": request.variable,
            "results": results.to_dicts(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analysis/two-way")
async def perform_two_way_analysis(request: TwoWayAnalysisRequest):
    """
    Perform two-way analysis.

    Args:
        request: Two-way analysis parameters

    Returns:
        Pivot table results
    """
    if state["analysis_data"] is None:
        raise HTTPException(
            status_code=400,
            detail="Create analysis dataset first",
        )

    try:
        config = state["study_config"]
        analyzer = TwoWayAnalyzer(
            state["analysis_data"],
            premium_type=config["premium_type"],
        )

        pivot = analyzer.analyze(
            request.variable_rows,
            request.variable_cols,
            request.metric,
        )

        interaction = analyzer.get_interaction_plot_data(
            request.variable_rows,
            request.variable_cols,
        )

        return {
            "success": True,
            "metric": request.metric,
            "pivot_table": pivot.to_dicts(),
            "interaction_plot": interaction,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/glm/fit")
async def fit_glm_model(request: GLMSpecification):
    """
    Fit GLM model with interaction analysis.

    Args:
        request: GLM specification

    Returns:
        Model results
    """
    if state["analysis_data"] is None:
        raise HTTPException(
            status_code=400,
            detail="Create analysis dataset first",
        )

    try:
        fitter = GLMFitter(use_glum=True)

        # Filter data
        analysis_df = state["analysis_data"].to_pandas()
        analysis_df = analysis_df[analysis_df["ClaimType"] == request.claim_type]

        # Fit model
        results = fitter.fit_model(
            grouped_data=analysis_df,
            full_data=analysis_df,  # TODO: Use actual full data
            response_var=request.response_variable,
            predictor_vars=request.variables,
            include_interaction=(request.interaction_type == "full"),
        )

        return {
            "success": True,
            "claim_type": request.claim_type,
            "response_variable": request.response_variable,
            "variables": request.variables,
            "model_results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get current application status."""
    return {
        "study_configured": state["study_config"] is not None,
        "premium_loaded": state["premium_data"] is not None,
        "claims_loaded": state["claims_data"] is not None,
        "consolidated": state["consolidated_data"] is not None,
        "analysis_ready": state["analysis_data"] is not None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
