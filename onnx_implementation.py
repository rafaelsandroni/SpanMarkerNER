import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from optimum.utils import DummyTextInputGenerator
from optimum.utils.normalized_config import NormalizedTextConfig
from optimum.exporters.onnx.config import TextEncoderOnnxConfig
from typing import Dict
from optimum.version import __version__
from optimum.exporters.onnx import export, validate_model_outputs
from span_marker import SpanMarkerModel

print(f"Optimum version: {__version__}")


class SpanMarkerDummyTextInputenerator(DummyTextInputGenerator):
    SUPPORTED_INPUT_NAMES = (
        "input_ids",
        "attention_mask",
        "position_ids",
        "start_marker_indices",
        "num_marker_pairs",
        "num_words",
        "document_ids",
        "sentence_ids",
    )

    def __init__(self, *args, **kwargs):
        super(SpanMarkerDummyTextInputenerator, self).__init__(*args, **kwargs)
        self.batch = 2
        self.sequence_length_encoder = 512

    def generate(self, input_name: str, framework: str = "pt", int_dtype: str = "int64", float_dtype: str = "fp32"):
        min_value = 0
        max_value = 2 if input_name in ["input_ids", "attention_mask", "position_ids"] else self.vocab_size
        if input_name in ["input_ids", "position_ids"]:
            shape = [self.batch, self.sequence_length_encoder]
        elif input_name == "attention_mask":
            shape = [self.batch, self.sequence_length_encoder, self.sequence_length_encoder]
        else:
            shape = [self.batch]

        return self.random_int_tensor(shape, max_value, min_value=min_value, framework=framework, dtype=int_dtype)


class SpanMarkerOnnxConfig(TextEncoderOnnxConfig):
    NORMALIZED_CONFIG_CLASS = NormalizedTextConfig
    DUMMY_INPUT_GENERATOR_CLASSES = (SpanMarkerDummyTextInputenerator,)
    DEFAULT_ONNX_OPSET = 14
    ATOL_FOR_VALIDATION = 1e-4

    @property
    def inputs(self) -> Dict[str, Dict[int, str]]:
        dynamic_axis = {0: "batch_size"}
        return {
            "input_ids": dynamic_axis,
            "attention_mask": dynamic_axis,
            "position_ids": dynamic_axis,
            "start_marker_indices": dynamic_axis,
            "num_marker_pairs": dynamic_axis,
            "num_words": dynamic_axis,
            "document_ids": dynamic_axis,
            "sentence_ids": dynamic_axis,
        }

    @property
    def outputs(self) -> Dict[str, Dict[int, str]]:
        dynamic_axis = {0: "batch_size"}
        return {
            "logits": dynamic_axis,
            "out_num_marker_pairs": dynamic_axis,
            "out_num_words": dynamic_axis,
            "out_document_ids": dynamic_axis,
            "out_sentence_ids": dynamic_axis,
        }


# TODO
# class SpanMarkerOnnxPipeline():


if __name__ == "__main__":
    # Load SpanMarker model
    repo_id = "lxyuan/span-marker-bert-base-multilingual-uncased-multinerd"
    base_model = SpanMarkerModel.from_pretrained(repo_id)
    base_model_config = base_model.config

    # Export to onnx
    onnx_path = Path("spanmarker_model.onnx")
    onnx_config = SpanMarkerOnnxConfig(base_model_config)
    onnx_inputs, onnx_outputs = export(
        base_model,
        SpanMarkerOnnxConfig(base_model.config, task="token-classification"),
        onnx_path,
    )

    # ONNX Validation
    validate_model_outputs(onnx_config, base_model, onnx_path, onnx_outputs, onnx_config.ATOL_FOR_VALIDATION)
