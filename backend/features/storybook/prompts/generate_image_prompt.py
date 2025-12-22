from dataclasses import dataclass
from enum import Enum


class ArtStyle(str, Enum):
    WATERCOLOR = "watercolor"
    VAN_GOGH = "van_gogh"
    FANTASY = "fantasy"
    CARTOON = "cartoon"


STYLE_PROMPTS = {
    ArtStyle.WATERCOLOR: "Fairy tale watercolor style, soft lines and pastel tones, warm and cozy atmosphere, friendly for children, subtle light and shadow",
    ArtStyle.VAN_GOGH: "Vincent van Gogh 'Starry Night' style, swirling brushstrokes and dramatic color contrasts, deep blues and bright yellows, artistic and mystical feeling, softened for fairy tale illustration",
    ArtStyle.FANTASY: "Fantasy illustration style, vivid and bright colors, magical atmosphere, soft texture and light, child-friendly fairy tale illustration",
    ArtStyle.CARTOON: "Cartoon style, clean outlines and bright colors, cute and cheerful atmosphere, simple details, playful fairy tale illustration",
}


@dataclass
class GenerateImagePrompt:
    stories: list[str]
    style_keyword: ArtStyle

    def render(self) -> str:
        diary_text = "\n".join(f"* {entry}" for entry in self.stories)

        return f"""
Transform the provided image into a children’s picture book illustration. Reference Image Rule: - Use the provided image as the single and exact reference. - Do not introduce new characters, objects, or background elements. Subject Preservation: - If a person is present, preserve the same facial features, hairstyle, proportions, pose, and expression. - Maintain the same clothing, accessories, and overall silhouette. - Do not redesign, idealize, or stylize the face beyond simplification. Style Transformation: - Change only the illustration style to a children’s storybook aesthetic. - Simplified shapes and forms - Flat or minimally layered perspective - Bold, clean outlines - Soft, warm, symbolic color palette - Gentle and calm mood suitable for a children’s book Cultural & Artistic Direction: - Soft, hand-painted picture-book illustration with a gentle, nostalgic warmth, designed for modern children’s books - Decorative composition with balanced visual rhythm - Avoid realism; favor illustrative clarity and warmth Background Treatment: - Keep the original background structure, but simplify details - Lower contrast and saturation in the background so the main subject stands out Constraints: - Do not change the scene composition - Do not alter facial identity - No photorealism - No text - No watermarks
"""


# v4 text_input = f"""
# Create a whimsical, storybook-style illustration in the style of {inputData.style} based on the story: {input_data.story}.
# Depict the main human characters as they are, and transform all other characters or background figures into animals appropriate for the scene.
# Show characters and key elements in dynamic motion, illustrating their actions and interactions with lively expressions and gestures.
# Do not include any text, letters, numbers, captions, speech bubbles, or signs in the image.
# Use vivid, magical, and charming details to enhance the fairy tale atmosphere.
# Focus on composition, lighting, and perspective as if using a low-angle or wide-angle camera to make the scene more immersive.
# Optionally, generate the illustration step by step: first background, then main characters, then additional animal characters, and finally magical effects or props.
# """
