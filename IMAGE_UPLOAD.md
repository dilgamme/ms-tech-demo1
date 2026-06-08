# Image Upload Composer

## Purpose

Image uploads use a staged attachment flow so a user can select an image and
then write an instruction before analysis begins.

## User Flow

1. The user selects a PNG, JPEG, or WebP image.
2. The composer keeps the image as a pending attachment.
3. A thumbnail, filename, and remove button appear above the message field.
4. The message field remains focused and accepts the image instruction.
5. Send submits the image and instruction together to the image analysis API.
6. Send remains disabled until the user writes an instruction.

Selecting an image no longer sends it immediately or clears text already typed
in the composer. The application does not insert a default image prompt.

## Implementation

- `frontend/src/components/ChatInput.jsx` owns the pending image and preview URL.
- Browser object URLs are revoked when the attachment changes or the component
  unmounts.
- `frontend/src/App.jsx` receives the image only when the combined form is
  submitted and then calls `/api/images/analyze`.
- The pending image can be removed without clearing the typed instruction.

## Verification

```bash
cd frontend
npm run build
```

Manual checks:

- Select an image and confirm no API request is sent immediately.
- Type an instruction and send; confirm the user message shows both image and
  instruction.
- Select an image with text already entered; confirm the text remains.
- Remove an attachment; confirm the text remains and normal text chat can send.
- Attach an image without text and confirm Send remains disabled.
