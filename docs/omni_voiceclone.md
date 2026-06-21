1. Install the javascript client (docs) if you don't already have it installed.


$ npm i -D @gradio/client
2. Find the API endpoint below corresponding to your desired function in the app. Copy the code snippet, replacing the placeholder values with your own input data. If this is a private Space, you may need to pass your Hugging Face token as well (read more). Or use the 
API Recorder

 to automatically generate your API requests.

API name: /_clone_fn 
1180 requests (65% successful, p50: 0 ms)
p50
0 ms
p90
0 ms
p99
0 ms
Most recently used

import { Client } from "@gradio/client";

const response_0 = await fetch("https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav");
const exampleAudio = await response_0.blob();

const client = await Client.connect("k2-fsa/OmniVoice");
const result = await client.predict("/_clone_fn", {
		text: "Hello!!",
		lang: "Auto",
		ref_aud: exampleAudio,
		ref_text: "Hello!!",
		instruct: "Hello!!",
		ns: 32,
		gs: 2.0,
		dn: true,
		sp: 1.0,
		du: 3,
		pp: true,
		po: true,
});

console.log(result.data);
Accepts 12 parameters:
text string Required

The input value that is provided in the "Text to Synthesize / 待合成文本" Textbox component.

lang string Default:"Auto"

The input value that is provided in the "Language (optional) / 语种 (可选)" Dropdown component.

ref_aud any Required

The input value that is provided in the "Reference Audio / 参考音频" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

ref_text string Required

The input value that is provided in the "Reference Text (optional) / 参考音频文本（可选）" Textbox component.

instruct string Required

The input value that is provided in the "Instruct" Textbox component.

ns number Default:32

The input value that is provided in the "Inference Steps" Slider component.

gs number Default:2

The input value that is provided in the "Guidance Scale (CFG)" Slider component.

dn boolean Default:True

The input value that is provided in the "Denoise" Checkbox component.

sp number Default:1

The input value that is provided in the "Speed" Slider component.

du number Required

The input value that is provided in the "Duration (seconds)" Number component.

pp boolean Default:True

The input value that is provided in the "Preprocess Prompt" Checkbox component.

po boolean Default:True

The input value that is provided in the "Postprocess Output" Checkbox component.

Returns list of 2 elements
[0]

The output value that appears in the "Output Audio / 合成结果" Audio component.

[1] string

The output value that appears in the "Status / 状态" Textbox component.

API name: /_design_fn 
212 requests (43% successful, p50: 0 ms)
p50
0 ms
p90
0 ms
p99
0 ms

import { Client } from "@gradio/client";

const client = await Client.connect("k2-fsa/OmniVoice");
const result = await client.predict("/_design_fn", {
		text: "Hello!!",
		lang: "Auto",
		ns: 32,
		gs: 2.0,
		dn: true,
		sp: 1.0,
		du: 3,
		pp: true,
		po: true,
		param_9: "Auto",
		param_10: "Auto",
		param_11: "Auto",
		param_12: "Auto",
		param_13: "Auto",
		param_14: "Auto",
});

console.log(result.data);
Accepts 15 parameters:
text string Required

The input value that is provided in the "Text to Synthesize / 待合成文本" Textbox component.

lang string Default:"Auto"

The input value that is provided in the "Language (optional) / 语种 (可选)" Dropdown component.

ns number Default:32

The input value that is provided in the "Inference Steps" Slider component.

gs number Default:2

The input value that is provided in the "Guidance Scale (CFG)" Slider component.

dn boolean Default:True

The input value that is provided in the "Denoise" Checkbox component.

sp number Default:1

The input value that is provided in the "Speed" Slider component.

du number Required

The input value that is provided in the "Duration (seconds)" Number component.

pp boolean Default:True

The input value that is provided in the "Preprocess Prompt" Checkbox component.

po boolean Default:True

The input value that is provided in the "Postprocess Output" Checkbox component.

param_9 string Default:"Auto"

The input value that is provided in the "Gender / 性别" Dropdown component.

param_10 string Default:"Auto"

The input value that is provided in the "Age / 年龄" Dropdown component.

param_11 string Default:"Auto"

The input value that is provided in the "Pitch / 音调" Dropdown component.

param_12 string Default:"Auto"

The input value that is provided in the "Style / 风格" Dropdown component.

param_13 string Default:"Auto"

The input value that is provided in the "English Accent / 英文口音" Dropdown component.

param_14 string Default:"Auto"

The input value that is provided in the "Chinese Dialect / 中文方言" Dropdown component.

Returns list of 2 elements
[0]

The output value that appears in the "Output Audio / 合成结果" Audio component.

[1] string

The output value that appears in the "Status / 状态" Textbox component.