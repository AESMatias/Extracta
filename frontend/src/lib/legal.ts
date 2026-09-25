// Terms and Conditions and Privacy Policy, in English and Spanish.
// Review them with a lawyer before launch, and set CONTACT_EMAIL to a real address you read.

import type { Locale } from "./preferences";

export const CONTACT_EMAIL = "support@extracta.example"; // TODO(owner): your real support address
export const LEGAL_UPDATED = "2026-09-25";

export interface LegalSection {
  title: string;
  paragraphs: string[];
}

export interface LegalDocument {
  title: string;
  intro: string;
  sections: LegalSection[];
}

const terms: Record<Locale, LegalDocument> = {
  en: {
    title: "Terms and Conditions",
    intro:
      "These terms govern the use of Extracta, a service operated by AESMatias that extracts structured data from PDF documents with artificial intelligence. By creating an account or using the service you accept them.",
    sections: [
      {
        title: "1. The service",
        paragraphs: [
          "Extracta reads the digital PDFs you upload, classifies them and extracts their data with an AI model, and lets you view it, chart it and export it to Excel, CSV or JSON.",
          "Results are produced automatically and may contain errors or omissions. You are responsible for reviewing them before relying on them, especially amounts, dates and tax identifiers. Extracta is not an accounting, tax or legal service.",
        ],
      },
      {
        title: "2. Accounts",
        paragraphs: [
          "You must be at least 18 years old and give truthful information. You are responsible for keeping your password safe and for all activity in your account. One account per person; accounts may not be shared or resold.",
          "Some features require confirming your email address. The administrator may approve, suspend or close accounts that break these terms.",
        ],
      },
      {
        title: "3. Acceptable use",
        paragraphs: [
          "You may only upload documents you have the right to process. It is forbidden to upload unlawful content, malware, or personal data of third parties without a legal basis to process it.",
          "It is also forbidden to try to bypass usage limits, overload or attack the service, access other users' data, or copy the service by automated means.",
        ],
      },
      {
        title: "4. Your content",
        paragraphs: [
          "You keep every right over your documents and the data extracted from them. You grant Extracta only the permission needed to process them and show you the results.",
          "The PDF file is deleted from our servers right after processing. Extracted data is stored only if you choose to save it to your history, until you delete it or close your account. Extracta does not use your documents to train AI models.",
        ],
      },
      {
        title: "5. Plans, pages and payments",
        paragraphs: [
          "Usage is measured in PDF pages: every page of every processed document counts once. If a document cannot be processed, its pages are given back.",
          "The Free plan includes a limited number of pages every 24 hours. Subscriptions give a number of pages every 30 days and renew automatically every month until cancelled. Page packs are prepaid pages that do not expire while the service operates, and they are used after your plan's pages.",
          "Prices are in US dollars and may include taxes depending on your country. Payments are processed by PayPal; Extracta never receives or stores your card details. Price changes never affect a period you already paid for.",
        ],
      },
      {
        title: "6. Cancellation",
        paragraphs: [
          "You can cancel a subscription at any time from your account. There will be no further charges and you keep your plan until the end of the period you paid for. Cancelling does not by itself give a refund; see section 11.",
        ],
      },
      {
        title: "7. Availability and changes",
        paragraphs: [
          "We work to keep Extracta available but do not guarantee uninterrupted service. We may change, improve or discontinue features. Important changes to these terms will be announced on the site or by email before they apply.",
        ],
      },
      {
        title: "8. Liability",
        paragraphs: [
          "The service is provided \"as is\". To the extent allowed by law, Extracta is not liable for indirect damages, lost profits, or decisions made on the basis of extracted data without reviewing it. Our total liability is limited to the amount you paid in the three months before the event.",
        ],
      },
      {
        title: "9. Suspension and closure",
        paragraphs: [
          "We may suspend or close accounts that break these terms. You can ask us to close your account at any time by writing to " + CONTACT_EMAIL + ".",
        ],
      },
      {
        title: "10. Law and contact",
        paragraphs: [
          "These terms are governed by the laws of the Republic of Chile. For any question write to " + CONTACT_EMAIL + ".",
        ],
      },
      {
        title: "11. Refunds",
        paragraphs: [
          "A payment is refunded only when both conditions are met: (a) none of the pages of the paid plan or page pack have been used, and (b) less than 72 hours have passed since the payment was made and the plan or pack was activated.",
          "To request it, write to " + CONTACT_EMAIL + " from the email of your account, including the PayPal transaction ID. Approved refunds are returned through PayPal to the original payment method, and the plan or the pages of the refunded pack are removed from your account. Each monthly subscription charge is evaluated on its own under these same conditions.",
        ],
      },
    ],
  },
  es: {
    title: "Términos y Condiciones",
    intro:
      "Estos términos regulan el uso de Extracta, un servicio operado por AESMatias que extrae datos estructurados de documentos PDF con inteligencia artificial. Al crear una cuenta o usar el servicio, los aceptas.",
    sections: [
      {
        title: "1. El servicio",
        paragraphs: [
          "Extracta lee los PDFs digitales que subes, los clasifica y extrae sus datos con un modelo de IA, y te permite verlos, graficarlos y exportarlos a Excel, CSV o JSON.",
          "Los resultados se generan de forma automática y pueden contener errores u omisiones. Eres responsable de revisarlos antes de usarlos, en especial montos, fechas e identificadores tributarios. Extracta no es un servicio contable, tributario ni legal.",
        ],
      },
      {
        title: "2. Cuentas",
        paragraphs: [
          "Debes tener al menos 18 años y entregar información verdadera. Eres responsable de cuidar tu contraseña y de toda la actividad de tu cuenta. Una cuenta por persona; no se pueden compartir ni revender.",
          "Algunas funciones requieren confirmar tu email. El administrador puede aprobar, suspender o cerrar cuentas que incumplan estos términos.",
        ],
      },
      {
        title: "3. Uso aceptable",
        paragraphs: [
          "Solo puedes subir documentos que tengas derecho a procesar. Está prohibido subir contenido ilícito, malware o datos personales de terceros sin una base legal para tratarlos.",
          "También está prohibido intentar saltarse los límites de uso, sobrecargar o atacar el servicio, acceder a datos de otros usuarios o copiar el servicio por medios automatizados.",
        ],
      },
      {
        title: "4. Tu contenido",
        paragraphs: [
          "Conservas todos los derechos sobre tus documentos y los datos extraídos de ellos. Solo le otorgas a Extracta el permiso necesario para procesarlos y mostrarte los resultados.",
          "El archivo PDF se borra de nuestros servidores apenas se procesa. Los datos extraídos se guardan solo si eliges guardarlos en tu historial, hasta que los borres o cierres tu cuenta. Extracta no usa tus documentos para entrenar modelos de IA.",
        ],
      },
      {
        title: "5. Planes, páginas y pagos",
        paragraphs: [
          "El uso se mide en páginas de PDF: cada página de cada documento procesado cuenta una vez. Si un documento no se puede procesar, sus páginas se devuelven.",
          "El plan Free incluye una cantidad limitada de páginas cada 24 horas. Las suscripciones entregan una cantidad de páginas cada 30 días y se renuevan automáticamente cada mes hasta que las canceles. Los paquetes de páginas son páginas prepagadas que no vencen mientras el servicio opere, y se usan después de las páginas de tu plan.",
          "Los precios están en dólares estadounidenses y pueden incluir impuestos según tu país. Los pagos los procesa PayPal; Extracta nunca recibe ni guarda los datos de tu tarjeta. Los cambios de precio nunca afectan un periodo que ya pagaste.",
        ],
      },
      {
        title: "6. Cancelación",
        paragraphs: [
          "Puedes cancelar una suscripción en cualquier momento desde tu cuenta. No habrá más cobros y mantienes tu plan hasta que termine el periodo pagado. Cancelar no da derecho por sí solo a un reembolso; ver la sección 11.",
        ],
      },
      {
        title: "7. Disponibilidad y cambios",
        paragraphs: [
          "Trabajamos para mantener Extracta disponible, pero no garantizamos un servicio ininterrumpido. Podemos cambiar, mejorar o discontinuar funciones. Los cambios importantes a estos términos se anunciarán en el sitio o por email antes de aplicarse.",
        ],
      },
      {
        title: "8. Responsabilidad",
        paragraphs: [
          "El servicio se entrega \"tal cual\". En la medida que la ley lo permita, Extracta no responde por daños indirectos, lucro cesante ni decisiones tomadas en base a datos extraídos sin revisarlos. Nuestra responsabilidad total se limita al monto que pagaste en los tres meses anteriores al hecho.",
        ],
      },
      {
        title: "9. Suspensión y cierre",
        paragraphs: [
          "Podemos suspender o cerrar cuentas que incumplan estos términos. Puedes pedirnos cerrar tu cuenta en cualquier momento escribiendo a " + CONTACT_EMAIL + ".",
        ],
      },
      {
        title: "10. Ley aplicable y contacto",
        paragraphs: [
          "Estos términos se rigen por las leyes de la República de Chile. Para cualquier consulta escribe a " + CONTACT_EMAIL + ".",
        ],
      },
      {
        title: "11. Reembolsos",
        paragraphs: [
          "Un pago se reembolsa solo cuando se cumplen ambas condiciones: (a) no se ha usado ninguna de las páginas del plan o paquete pagado, y (b) han pasado menos de 72 horas desde que se realizó el pago y se activó el plan o paquete.",
          "Para solicitarlo, escribe a " + CONTACT_EMAIL + " desde el email de tu cuenta indicando el ID de la transacción de PayPal. Los reembolsos aprobados se devuelven por PayPal al medio de pago original, y se retira de tu cuenta el plan o las páginas del paquete reembolsado. Cada cobro mensual de una suscripción se evalúa por separado con estas mismas condiciones.",
        ],
      },
    ],
  },
};

const privacy: Record<Locale, LegalDocument> = {
  en: {
    title: "Privacy Policy",
    intro:
      "This policy explains what data Extracta collects, why, with whom it is shared and what rights you have. Extracta is operated by AESMatias, who is responsible for this processing. Contact: " + CONTACT_EMAIL + ".",
    sections: [
      {
        title: "1. Data we collect",
        paragraphs: [
          "Account: email, name, a one-way hash of your password (never the password itself) and, if you use it, your Google account identifier.",
          "Documents: the PDFs you upload, which are deleted right after processing, and the data extracted from them. In process-only mode that data is kept for 1 hour and never written to a database; it is stored only if you choose to save it to your history.",
          "Usage and payments: pages processed and when, the plan and page packs you bought, and the PayPal references of each payment. We never receive card numbers.",
          "Technical: IP address and browser information in server logs and in short-lived counters used to stop abuse (rate limits).",
        ],
      },
      {
        title: "2. Why we use it",
        paragraphs: [
          "To provide the service you asked for (contract), to keep it secure and prevent abuse (legitimate interest), to process payments and meet tax obligations (legal obligation), and to send you service emails such as email confirmation, password resets and security notices. We do not send advertising and we do not sell your data.",
        ],
      },
      {
        title: "3. Who processes it for us",
        paragraphs: [
          "Google (Gemini API): the text of your documents is sent to it to extract the data. Supabase: database. PayPal: payments. Google Sign-In: only if you choose it. An email provider: to deliver service emails. The hosting provider of our servers.",
          "Some of these providers may process data outside your country, under their own contractual and security safeguards.",
        ],
      },
      {
        title: "4. How long we keep it",
        paragraphs: [
          "PDF files: deleted right after processing (any left behind by an error are removed within hours). Process-only results: 1 hour. Saved documents: until you delete them or close your account. Account data: while your account is active. Payment records: as long as tax law requires.",
        ],
      },
      {
        title: "5. Cookies and browser storage",
        paragraphs: [
          "We use a single strictly necessary cookie to keep you signed in. Your browser also stores your theme, language and your current batch of results. There are no advertising or tracking cookies.",
        ],
      },
      {
        title: "6. Security",
        paragraphs: [
          "Encrypted connections (HTTPS), passwords stored with slow salted hashes, database access limited per account, security headers, patched and scanned servers, and payments handled entirely by PayPal. No system is invulnerable; if an incident affects your data we will notify you as the law requires.",
        ],
      },
      {
        title: "7. Your rights",
        paragraphs: [
          "You can access, correct, export (with the Excel, CSV and JSON exports), and delete your data, object to its processing and ask us to close your account by writing to " +
            CONTACT_EMAIL +
            ". You may also complain to your data protection authority.",
        ],
      },
      {
        title: "8. Minors and changes",
        paragraphs: [
          "Extracta is not intended for people under 18. We will announce important changes to this policy on the site or by email before they apply.",
        ],
      },
    ],
  },
  es: {
    title: "Política de Privacidad",
    intro:
      "Esta política explica qué datos recopila Extracta, para qué, con quién se comparten y qué derechos tienes. Extracta es operado por AESMatias, responsable de este tratamiento. Contacto: " + CONTACT_EMAIL + ".",
    sections: [
      {
        title: "1. Datos que recopilamos",
        paragraphs: [
          "Cuenta: email, nombre, un hash irreversible de tu contraseña (nunca la contraseña) y, si lo usas, el identificador de tu cuenta de Google.",
          "Documentos: los PDFs que subes, que se borran apenas se procesan, y los datos extraídos de ellos. En modo solo procesar esos datos se conservan 1 hora y nunca se escriben en una base de datos; solo se guardan si eliges guardarlos en tu historial.",
          "Uso y pagos: páginas procesadas y cuándo, el plan y los paquetes de páginas que compraste, y las referencias de PayPal de cada pago. Nunca recibimos números de tarjeta.",
          "Técnicos: dirección IP e información del navegador en los registros del servidor y en contadores de corta duración usados para frenar abusos (límites de intentos).",
        ],
      },
      {
        title: "2. Para qué los usamos",
        paragraphs: [
          "Para entregarte el servicio que pediste (contrato), mantenerlo seguro y evitar abusos (interés legítimo), procesar pagos y cumplir obligaciones tributarias (obligación legal), y enviarte emails del servicio como la confirmación de tu email, el cambio de contraseña y avisos de seguridad. No enviamos publicidad ni vendemos tus datos.",
        ],
      },
      {
        title: "3. Quién los trata por nosotros",
        paragraphs: [
          "Google (API de Gemini): se le envía el texto de tus documentos para extraer los datos. Supabase: base de datos. PayPal: pagos. Google Sign-In: solo si lo eliges. Un proveedor de email: para enviar los emails del servicio. El proveedor de hosting de nuestros servidores.",
          "Algunos de estos proveedores pueden tratar datos fuera de tu país, bajo sus propias garantías contractuales y de seguridad.",
        ],
      },
      {
        title: "4. Cuánto tiempo los guardamos",
        paragraphs: [
          "Archivos PDF: se borran apenas se procesan (los que quedan por un error se eliminan en pocas horas). Resultados de solo procesar: 1 hora. Documentos guardados: hasta que los borres o cierres tu cuenta. Datos de la cuenta: mientras esté activa. Registros de pago: el tiempo que exija la ley tributaria.",
        ],
      },
      {
        title: "5. Cookies y almacenamiento del navegador",
        paragraphs: [
          "Usamos una sola cookie estrictamente necesaria para mantener tu sesión. Tu navegador además guarda tu tema, tu idioma y tu lote actual de resultados. No hay cookies de publicidad ni de seguimiento.",
        ],
      },
      {
        title: "6. Seguridad",
        paragraphs: [
          "Conexiones cifradas (HTTPS), contraseñas guardadas con hashes lentos con sal, acceso a la base de datos limitado por cuenta, cabeceras de seguridad, servidores parchados y escaneados, y pagos manejados completamente por PayPal. Ningún sistema es invulnerable; si un incidente afecta tus datos te avisaremos como exija la ley.",
        ],
      },
      {
        title: "7. Tus derechos",
        paragraphs: [
          "Puedes acceder, corregir, exportar (con las exportaciones a Excel, CSV y JSON) y borrar tus datos, oponerte a su tratamiento y pedirnos cerrar tu cuenta escribiendo a " +
            CONTACT_EMAIL +
            ". También puedes reclamar ante la autoridad de protección de datos de tu país.",
        ],
      },
      {
        title: "8. Menores y cambios",
        paragraphs: [
          "Extracta no está dirigido a menores de 18 años. Anunciaremos los cambios importantes a esta política en el sitio o por email antes de que se apliquen.",
        ],
      },
    ],
  },
};

export const LEGAL = { terms, privacy };
