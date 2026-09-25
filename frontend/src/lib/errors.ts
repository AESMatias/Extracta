// The API answers in English. For Spanish visitors, known messages are translated here; anything
// unknown is shown as the API wrote it.

import type { Locale } from "./preferences";

const EXACT_ES: Record<string, string> = {
  "An account with this email already exists. Sign in instead.": "Ya existe una cuenta con este email. Inicia sesión.",
  "Another upload from your account is still in progress. Wait for it to finish.": "Otra subida de tu cuenta sigue en curso. Espera a que termine.",
  "Choose a page pack.": "Elige un paquete de páginas.",
  "Choose a paid plan.": "Elige un plan de pago.",
  "Confirm your email address first: open the link we sent you.": "Primero confirma tu email: abre el link que te enviamos.",
  "Document not found.": "Documento no encontrado.",
  "Enter a valid email address.": "Escribe un email válido.",
  "Incorrect email or password.": "Email o contraseña incorrectos.",
  "Payments are not configured yet.": "Los pagos aún no están configurados.",
  "Saving documents to the database is available on paid plans and page packs.":
    "Guardar documentos en el historial está disponible en los planes de pago y con paquetes de páginas.",
  "Send at least one PDF in the 'files' field.": "Envía al menos un PDF.",
  "Sign in to continue.": "Inicia sesión para continuar.",
  "The password cannot be your email address.": "La contraseña no puede ser tu email.",
  "This PDF could not be opened (damaged or password-protected).": "No se pudo abrir este PDF (dañado o protegido con contraseña).",
  "This PDF has no pages.": "Este PDF no tiene páginas.",
  "This account is suspended. Contact the administrator.": "Esta cuenta está suspendida. Contacta al administrador.",
  "This account request was rejected.": "Esta solicitud de cuenta fue rechazada.",
  "This link is invalid or has expired.": "Este link no es válido o venció.",
  "This link is invalid, expired or was already used. Ask for a new one.": "Este link no es válido, venció o ya se usó. Pide uno nuevo.",
  "Too many attempts. Wait a few minutes and try again.": "Demasiados intentos. Espera unos minutos y vuelve a intentarlo.",
  "Your Google email address is not verified.": "Tu email de Google no está verificado.",
  "Your account is waiting for approval by the administrator.": "Tu cuenta espera la aprobación del administrador.",
  "Your current password is not correct.": "Tu contraseña actual no es correcta.",
  "No pages left": "No quedan páginas",
  "file is not a PDF": "el archivo no es un PDF",
  "The upload is too large. Send fewer or smaller files.": "La subida es muy grande. Envía menos archivos o más livianos.",
  "Cross-site request refused.": "Solicitud rechazada por seguridad.",
  "PayPal is not available right now. Try again in a moment.": "PayPal no está disponible ahora. Inténtalo en un momento.",
  "Could not complete the payment with PayPal. You were not charged twice; try again.":
    "No se pudo completar el pago con PayPal. No se te cobró dos veces; inténtalo de nuevo.",
  "Could not confirm the subscription with PayPal. It will be applied automatically in a few minutes.":
    "No se pudo confirmar la suscripción con PayPal. Se aplicará sola en unos minutos.",
  "The order amount does not match the pack price.": "El monto de la orden no coincide con el precio del paquete.",
  "The payment was not completed.": "El pago no se completó.",
  "You already have a subscription. Cancel it first to change plans.": "Ya tienes una suscripción. Cancélala primero para cambiar de plan.",
  "You have no active subscription.": "No tienes una suscripción activa.",
  "Order not found.": "Orden no encontrada.",
  "Subscription not found.": "Suscripción no encontrada.",
  "This PDF has no text layer (it looks scanned). Scanned documents need OCR, not supported yet.":
    "Este PDF no tiene capa de texto (parece escaneado). Los escaneos necesitan OCR, que aún no se soporta.",
  "This PDF is damaged or password-protected and cannot be read.": "Este PDF está dañado o protegido con contraseña y no se puede leer.",
  "The AI service is busy right now. Please upload the document again in a few minutes.":
    "El servicio de IA está ocupado. Vuelve a subir el documento en unos minutos.",
  "The document could not be converted into structured data.": "El documento no se pudo convertir en datos estructurados.",
  "The file waited too long in the queue and was removed. Upload it again.": "El archivo esperó demasiado en la cola y se eliminó. Súbelo de nuevo.",
  "This PDF expands to an unsafe size when opened (a possible decompression bomb) and was rejected.":
    "Este PDF se expande a un tamaño inseguro al abrirse (una posible bomba de descompresión) y fue rechazado.",
  "This PDF is too complex to process safely and was rejected.": "Este PDF es demasiado complejo para procesarlo de forma segura y fue rechazado.",
  "This PDF took too long to read and was stopped.": "Este PDF tardó demasiado en leerse y se detuvo.",
  "This PDF could not be processed safely and was rejected.": "Este PDF no se pudo procesar de forma segura y fue rechazado.",
  "Network error: check your connection and try again.": "Error de red: revisa tu conexión e inténtalo de nuevo.",
  "Network error: the upload did not reach the server.": "Error de red: la subida no llegó al servidor.",
};

const PATTERNS_ES: [RegExp, string][] = [
  [/^Use a password between (\d+) and (\d+) characters\.$/, "Usa una contraseña de entre $1 y $2 caracteres."],
  [/^Your (\w+) plan allows (\d+) files per upload\.$/, "Tu plan $1 permite $2 archivos por subida."],
  [/^(\d+) pages: only (\d+) pages left\.$/, "$1 páginas: solo quedan $2."],
  [/^(\d+) pages: your plan reads up to (\d+) pages per PDF\.$/, "$1 páginas: tu plan lee hasta $2 páginas por PDF."],
  [/^file is larger than (\d+) MB$/, "el archivo pesa más de $1 MB"],
  [
    /^You used your (\d+) pages for these 24 hours\. (.*)$/,
    "Usaste tus $1 páginas de estas 24 horas. Compra un paquete de páginas o mejora tu plan para seguir.",
  ],
  [
    /^You used your (\d+) pages for these 30 days\. (.*)$/,
    "Usaste tus $1 páginas de estos 30 días. Compra un paquete de páginas o mejora tu plan para seguir.",
  ],
  [/^Request failed \(HTTP (\d+)\)\.$/, "La solicitud falló (HTTP $1)."],
  [/^Upload failed \(HTTP (\d+)\)\.$/, "La subida falló (HTTP $1)."],
];

export function localizeError(message: string | null | undefined, locale: Locale): string {
  if (!message) return "";
  if (locale === "en") return message;
  const exact = EXACT_ES[message];
  if (exact) return exact;
  for (const [pattern, replacement] of PATTERNS_ES) {
    if (pattern.test(message)) return message.replace(pattern, replacement);
  }
  return message;
}

/** The message to show for any caught error, in the visitor's language. */
export function errorText(error: unknown, locale: Locale, fallback: string): string {
  if (error && typeof error === "object" && "message" in error && "status" in error) {
    return localizeError(String((error as { message: unknown }).message), locale) || fallback;
  }
  return fallback;
}
