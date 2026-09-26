// Terms and Conditions and Privacy Policy, in English and Spanish. Have a lawyer review them.

import type { Locale } from "./preferences";

export const CONTACT_EMAIL = "plutarco1677@gmail.com";
export const LEGAL_UPDATED = "2026-09-25";

export interface LegalSection {
  id?: string; // anchor, e.g. /terms#refunds
  title: string;
  paragraphs: string[];
  bullets?: string[];
  after?: string[]; // paragraphs after the bullets
}

export interface LegalDocument {
  title: string;
  intro: string;
  sections: LegalSection[];
}

const E = CONTACT_EMAIL;

const terms: Record<Locale, LegalDocument> = {
  en: {
    title: "Terms and Conditions",
    intro:
      "These terms apply when you use Extracta, create an account, subscribe to a plan or buy page packs. By creating an account or paying you confirm that you have read and accept them, including the refund policy in section 13.",
    sections: [
      {
        title: "1. Who provides the service",
        paragraphs: [`Extracta is a service operated by AESMatias, an independent developer based in Chile ("we", "us"). Contact: ${E}.`],
      },
      {
        title: "2. The service",
        paragraphs: [
          "Extracta reads the documents you upload (PDFs, images and XML e-invoices), classifies them and extracts their data with an AI model, and lets you view it, chart it and export it to Excel, CSV or JSON.",
          "Results are produced automatically and may contain errors or omissions. You are responsible for reviewing them before relying on them, especially amounts, dates and tax identifiers. Extracta is not an accounting, tax or legal service, and its results are not advice.",
        ],
      },
      {
        title: "3. Accounts",
        paragraphs: [
          "You must be at least 18 years old and give accurate information. You are responsible for keeping your password safe and for all activity in your account. One account per person; accounts may not be shared or resold.",
          "Some features require confirming your email address. We may approve, suspend or close accounts that break these terms.",
        ],
      },
      {
        title: "4. Acceptable use",
        paragraphs: ["When you use Extracta you must not:"],
        bullets: [
          "upload documents you have no right to process, unlawful content or malware;",
          "upload personal data of other people without a legal basis to process it;",
          "try to bypass usage limits, disrupt or overload the service, or access data that is not yours;",
          "copy or resell the service by automated means.",
        ],
        after: ["We may limit or block access in those cases."],
      },
      {
        title: "5. Your content",
        paragraphs: [
          "You keep every right over your documents and the data extracted from them. You give us only the permission needed to process them and show you the results. The Extracta software, brand and site remain ours; third-party tools and services keep their own licences.",
          "The uploaded file is deleted from our servers right after processing, and images lose their metadata (including location) before they are read. Extracted data is stored only if you choose to save it to your history, until you delete it or close your account. We do not use your documents to train AI models. Make sure you have the rights to every document you upload.",
        ],
      },
      {
        title: "6. Plans, pages and payments",
        paragraphs: [],
        bullets: [
          "Usage is measured in pages: every page of every processed PDF counts once, and an image or an XML e-invoice counts as one page. If a document cannot be processed, its pages are given back.",
          "The Free plan includes a limited number of pages every 24 hours.",
          "Subscriptions give a number of pages every 30 days and renew automatically every month until you cancel them.",
          "Page packs are prepaid pages that do not expire while the service operates. They are used after your plan's pages.",
          "Prices are shown in the currency displayed next to them (US dollars) and may include taxes depending on your country. Price changes never affect a period or a pack you already paid for.",
          "Payments are processed by PayPal. Your card details are entered in PayPal's own window and never reach our servers.",
        ],
      },
      {
        title: "7. Cancellation",
        paragraphs: [
          "You can cancel a subscription at any time from your account. There will be no further charges and you keep your plan until the end of the period you paid for. Cancelling does not by itself give a refund; see section 13.",
        ],
      },
      {
        title: "8. Availability and changes to the service",
        paragraphs: [
          "We work with professional care to keep Extracta available, but we do not guarantee uninterrupted service. We may change, improve or discontinue features; if we discontinue the service, prepaid pages that have not been used will be refunded.",
        ],
      },
      {
        title: "9. Limitation of liability",
        paragraphs: [
          "The service is provided \"as is\". To the extent the law allows, we are not liable for indirect losses, such as lost profits or lost data, or for decisions made on the basis of extracted data without reviewing it. Our total liability is limited to the amount you paid us in the three months before the event. Nothing in these terms limits rights that consumer protection law gives you and that cannot be waived.",
        ],
      },
      {
        title: "10. Suspension and closure",
        paragraphs: [
          `We may suspend or close accounts that break these terms. You can delete your account at any time: from your account page, with the form at /delete-account (we email your account a confirmation link), or by writing to ${E} from the email of your account, in which case we delete it within 48 hours and confirm by email.`,
        ],
      },
      {
        title: "11. Changes to these terms",
        paragraphs: [
          "We may update these terms; the date at the top shows the latest version and important changes will be announced on the site or by email. The version published when you make a payment is the one that applies to that payment.",
        ],
      },
      {
        title: "12. Governing law",
        paragraphs: [
          `These terms are governed by the laws of Chile. Before any formal claim, please write to ${E} so we can try to solve the issue together. This does not affect your right to go to the consumer protection authority (SERNAC) or the competent courts.`,
        ],
      },
      {
        id: "refunds",
        title: "13. Refunds",
        paragraphs: ["A payment for a plan or a page pack is refunded only when both conditions are met:"],
        bullets: [
          "none of the pages of the paid plan or page pack have been used; and",
          "less than 72 hours have passed since the payment was made and the plan or pack was activated.",
        ],
        after: [
          "Regardless of those conditions, a payment is refunded in full when you were charged twice or by mistake, or when we cannot provide the service you paid for. Each monthly subscription charge is evaluated on its own.",
          `To ask for a refund, write to ${E} from the email of your account, including the PayPal transaction ID. Approved refunds go back to the original payment method through PayPal; your bank or card issuer may take 5 to 10 business days to show them. Once refunded, the plan or the pages of the pack are removed from your account.`,
          "Because the pages are delivered and can be used as soon as the payment is completed, and to the extent the law allows, the right of withdrawal (derecho de retracto) under article 3 bis of Chilean Law 19.496 does not apply once any of the conditions above is no longer met. This does not limit any legal guarantee you are entitled to if we fail to provide the service.",
        ],
      },
    ],
  },
  es: {
    title: "Términos y Condiciones",
    intro:
      "Estos términos se aplican cuando usas Extracta, creas una cuenta, te suscribes a un plan o compras paquetes de páginas. Al crear una cuenta o pagar confirmas que los leíste y aceptas, incluida la política de reembolsos de la sección 13.",
    sections: [
      {
        title: "1. Quién presta el servicio",
        paragraphs: [`Extracta es un servicio operado por AESMatias, desarrollador independiente con base en Chile ("nosotros"). Contacto: ${E}.`],
      },
      {
        title: "2. El servicio",
        paragraphs: [
          "Extracta lee los documentos que subes (PDFs, imágenes y facturas electrónicas XML), los clasifica y extrae sus datos con un modelo de IA, y te permite verlos, graficarlos y exportarlos a Excel, CSV o JSON.",
          "Los resultados se generan de forma automática y pueden contener errores u omisiones. Eres responsable de revisarlos antes de usarlos, en especial montos, fechas e identificadores tributarios. Extracta no es un servicio contable, tributario ni legal, y sus resultados no son asesoría.",
        ],
      },
      {
        title: "3. Cuentas",
        paragraphs: [
          "Debes tener al menos 18 años y entregar información correcta. Eres responsable de cuidar tu contraseña y de toda la actividad de tu cuenta. Una cuenta por persona; no se pueden compartir ni revender.",
          "Algunas funciones requieren confirmar tu email. Podemos aprobar, suspender o cerrar cuentas que incumplan estos términos.",
        ],
      },
      {
        title: "4. Uso aceptable",
        paragraphs: ["Al usar Extracta no debes:"],
        bullets: [
          "subir documentos que no tengas derecho a procesar, contenido ilícito o malware;",
          "subir datos personales de otras personas sin una base legal para tratarlos;",
          "intentar saltarte los límites de uso, interrumpir o sobrecargar el servicio, o acceder a datos que no son tuyos;",
          "copiar o revender el servicio por medios automatizados.",
        ],
        after: ["En esos casos podemos limitar o bloquear el acceso."],
      },
      {
        title: "5. Tu contenido",
        paragraphs: [
          "Conservas todos los derechos sobre tus documentos y los datos extraídos de ellos. Solo nos das el permiso necesario para procesarlos y mostrarte los resultados. El software, la marca y el sitio de Extracta siguen siendo nuestros; las herramientas y servicios de terceros mantienen sus propias licencias.",
          "El archivo subido se borra de nuestros servidores apenas se procesa, y a las imágenes se les quitan sus metadatos (incluida la ubicación) antes de leerlas. Los datos extraídos se guardan solo si eliges guardarlos en tu historial, hasta que los borres o cierres tu cuenta. No usamos tus documentos para entrenar modelos de IA. Asegúrate de tener los derechos sobre cada documento que subas.",
        ],
      },
      {
        title: "6. Planes, páginas y pagos",
        paragraphs: [],
        bullets: [
          "El uso se mide en páginas: cada página de cada PDF procesado cuenta una vez, y una imagen o una factura electrónica XML cuenta como una página. Si un documento no se puede procesar, sus páginas se devuelven.",
          "El plan Free incluye una cantidad limitada de páginas cada 24 horas.",
          "Las suscripciones entregan una cantidad de páginas cada 30 días y se renuevan automáticamente cada mes hasta que las canceles.",
          "Los paquetes de páginas son páginas prepagadas que no vencen mientras el servicio opere. Se usan después de las páginas de tu plan.",
          "Los precios se muestran en la moneda indicada junto a ellos (dólares estadounidenses) y pueden incluir impuestos según tu país. Los cambios de precio nunca afectan un periodo o un paquete que ya pagaste.",
          "Los pagos los procesa PayPal. Los datos de tu tarjeta se ingresan en la ventana de PayPal y nunca llegan a nuestros servidores.",
        ],
      },
      {
        title: "7. Cancelación",
        paragraphs: [
          "Puedes cancelar una suscripción en cualquier momento desde tu cuenta. No habrá más cobros y mantienes tu plan hasta que termine el periodo pagado. Cancelar no da derecho por sí solo a un reembolso; ver la sección 13.",
        ],
      },
      {
        title: "8. Disponibilidad y cambios en el servicio",
        paragraphs: [
          "Trabajamos con cuidado profesional para mantener Extracta disponible, pero no garantizamos un servicio ininterrumpido. Podemos cambiar, mejorar o discontinuar funciones; si discontinuamos el servicio, reembolsaremos las páginas prepagadas que no se hayan usado.",
        ],
      },
      {
        title: "9. Limitación de responsabilidad",
        paragraphs: [
          "El servicio se entrega \"tal cual\". En la medida que la ley lo permita, no respondemos por pérdidas indirectas, como lucro cesante o pérdida de datos, ni por decisiones tomadas en base a datos extraídos sin revisarlos. Nuestra responsabilidad total se limita al monto que nos pagaste en los tres meses anteriores al hecho. Nada en estos términos limita los derechos irrenunciables que te da la ley de protección al consumidor.",
        ],
      },
      {
        title: "10. Suspensión y cierre",
        paragraphs: [
          `Podemos suspender o cerrar cuentas que incumplan estos términos. Puedes eliminar tu cuenta cuando quieras: desde la página de tu cuenta, con el formulario de /delete-account (enviamos a tu cuenta un link de confirmación), o escribiendo a ${E} desde el email de tu cuenta, en cuyo caso la eliminamos dentro de 48 horas y te confirmamos por email.`,
        ],
      },
      {
        title: "11. Cambios a estos términos",
        paragraphs: [
          "Podemos actualizar estos términos; la fecha al inicio indica la versión vigente y los cambios importantes se anunciarán en el sitio o por email. La versión publicada al momento de hacer un pago es la que se aplica a ese pago.",
        ],
      },
      {
        title: "12. Ley aplicable",
        paragraphs: [
          `Estos términos se rigen por las leyes de Chile. Antes de cualquier reclamo formal, escríbenos a ${E} para intentar resolverlo juntos. Esto no afecta tu derecho a acudir al Servicio Nacional del Consumidor (SERNAC) o a los tribunales competentes.`,
        ],
      },
      {
        id: "refunds",
        title: "13. Reembolsos",
        paragraphs: ["El pago de un plan o de un paquete de páginas se reembolsa solo cuando se cumplen ambas condiciones:"],
        bullets: [
          "no se ha usado ninguna de las páginas del plan o del paquete pagado; y",
          "han pasado menos de 72 horas desde que se realizó el pago y se activó el plan o el paquete.",
        ],
        after: [
          "Sin importar esas condiciones, un pago se reembolsa completo cuando se te cobró dos veces o por error, o cuando no podemos entregar el servicio que pagaste. Cada cobro mensual de una suscripción se evalúa por separado.",
          `Para pedir un reembolso, escribe a ${E} desde el email de tu cuenta, indicando el ID de la transacción de PayPal. Los reembolsos aprobados vuelven al medio de pago original a través de PayPal; tu banco o emisor de tarjeta puede tardar de 5 a 10 días hábiles en reflejarlos. Una vez reembolsado, se retira de tu cuenta el plan o las páginas del paquete.`,
          "Como las páginas se entregan y pueden usarse apenas se completa el pago, y en la medida que la ley lo permita, el derecho de retracto del artículo 3 bis de la Ley 19.496 no se aplica una vez que deja de cumplirse cualquiera de las condiciones anteriores. Esto no limita ninguna garantía legal que te corresponda si no entregamos el servicio.",
        ],
      },
    ],
  },
};

const privacy: Record<Locale, LegalDocument> = {
  en: {
    title: "Privacy Policy",
    intro: "This policy explains what personal data Extracta collects when you use it, why, who it is shared with and the rights you have over it.",
    sections: [
      {
        title: "1. Who is responsible for your data",
        paragraphs: [
          `Extracta is a service operated by AESMatias, an independent developer based in Chile ("we", "us"). We are the data controller for the personal data described here. For any question or request about your data, write to ${E}.`,
        ],
      },
      {
        title: "2. What data we collect",
        paragraphs: [],
        bullets: [
          "Your account: email, name, a one-way hash of your password (never the password itself) and, if you use Google sign-in, your Google account identifier.",
          "Your documents: the files you upload (PDFs, images and XML e-invoices; images lose their metadata, including location, before they are read), deleted right after processing, and the data extracted from them. In process-only mode that data is kept for 1 hour and never written to a database; it is stored only if you choose to save it to your history.",
          "Usage and payments: the pages you process and when, your plan, the page packs you buy, and for each payment the status, amount, currency and PayPal's reference numbers. Card details are entered in PayPal's window and never reach our servers.",
          "Technical data: your IP address, used for a short time (up to one hour) in server memory to limit sign-in attempts and prevent abuse, and not stored in our database; and the standard request logs of our servers, kept for security and troubleshooting.",
        ],
      },
      {
        title: "3. Documents and artificial intelligence",
        paragraphs: [
          "To extract the data, the text of your documents is sent to Google's Gemini API. We do not use your documents to train AI models. Google processes the text under its own terms and, depending on the service tier, may use it to improve its products.",
          "Please do not upload documents with sensitive information you do not need to process (for example health data or passwords), and only upload other people's data when you have the right to.",
        ],
      },
      {
        title: "4. Cookies and browser storage",
        paragraphs: [
          "We do not use advertising or analytics cookies, and we do not track you across other websites. Extracta only uses what it needs to work:",
        ],
        bullets: [
          "a session cookie that keeps you signed in (and a separate one for the owner's admin panel, never set for visitors);",
          "your light or dark theme and your language, saved in your browser;",
          "your current batch of results, saved in your browser so a reload does not lose it;",
          "cookies PayPal sets in its payment window to prevent fraud.",
        ],
        after: [
          "Because these are strictly necessary, we do not ask for cookie consent.",
          "To know how many people visit the site, we count unique visitors without cookies: your IP address and browser are turned into an irreversible code that only adds one to a daily total. Only the totals are kept (for up to 400 days); we never store your address or that code, and we cannot tell who visited.",
        ],
      },
      {
        title: "5. Why we use your data",
        paragraphs: [],
        bullets: [
          "To provide the service you asked for: your account, processing your documents, your plan and your payments.",
          "To send you service emails: email confirmation, password resets and security notices. We do not send advertising.",
          "To meet legal obligations, such as keeping accounting and tax records.",
          "To keep the service secure and prevent abuse, which is our legitimate interest.",
        ],
        after: ["We never sell your data and we do not use it for advertising."],
      },
      {
        title: "6. Who we share it with",
        paragraphs: ["We only share data with the providers that run Extracta, and only what each one needs:"],
        bullets: [
          "Google (Gemini API): extracting the data of your documents; and Google Sign-In, only if you use it.",
          "Supabase: database hosting.",
          "PayPal: payment processing.",
          "An email delivery provider: sending service emails.",
          "Our server hosting provider.",
        ],
        after: ["We may also disclose data when required by law or by a court or public authority."],
      },
      {
        title: "7. International transfers",
        paragraphs: [
          "These providers may store and process data outside Chile, including in the United States and the European Union. They apply their own security measures and contractual safeguards for these transfers.",
        ],
      },
      {
        title: "8. How long we keep it",
        paragraphs: [],
        bullets: [
          "Uploaded files: deleted right after processing; any left behind by an error are removed within hours.",
          "Process-only results: 1 hour.",
          "Saved documents: until you delete them or close your account.",
          "Account data: while your account is active, and deleted when you ask us to close it, unless the law requires us to keep something.",
          "Payment records: for the period required by tax and accounting law.",
        ],
      },
      {
        title: "9. Your rights",
        paragraphs: ["You can ask us at any time to:"],
        bullets: [
          "access the personal data we hold about you;",
          "correct data that is wrong or incomplete;",
          "delete your data, when we are not legally required to keep it;",
          "object to or restrict how we use it;",
          "receive a copy of it in a portable format (you can also export your documents to Excel, CSV or JSON yourself).",
        ],
        after: [
          `Write to ${E} from the email of your account. We reply within 30 days. You can also complain to the data protection or consumer authority of your country.`,
          "To delete your account and its data yourself, use the button on your account page or the form at /delete-account; requests sent by email are completed within 48 hours.",
        ],
      },
      {
        title: "10. Security",
        paragraphs: [
          "Data travels over encrypted connections (HTTPS), passwords are stored as slow salted hashes, each account can only reach its own data in the database, and card details are handled only by PayPal. No system is completely secure, but we take reasonable measures to protect your data and will notify you as the law requires if an incident affects it.",
        ],
      },
      {
        title: "11. Children",
        paragraphs: ["Extracta is intended for adults and businesses. We do not knowingly collect data from anyone under 18."],
      },
      {
        title: "12. Changes to this policy",
        paragraphs: ["We may update this policy. The date at the top shows the latest version, and significant changes will be highlighted on the site or sent by email."],
      },
    ],
  },
  es: {
    title: "Política de Privacidad",
    intro: "Esta política explica qué datos personales recopila Extracta cuando lo usas, para qué, con quién se comparten y qué derechos tienes sobre ellos.",
    sections: [
      {
        title: "1. Quién es responsable de tus datos",
        paragraphs: [
          `Extracta es un servicio operado por AESMatias, desarrollador independiente con base en Chile ("nosotros"). Somos los responsables del tratamiento de los datos personales descritos aquí. Para cualquier consulta o solicitud sobre tus datos, escribe a ${E}.`,
        ],
      },
      {
        title: "2. Qué datos recopilamos",
        paragraphs: [],
        bullets: [
          "Tu cuenta: email, nombre, un hash irreversible de tu contraseña (nunca la contraseña) y, si usas el acceso con Google, el identificador de tu cuenta de Google.",
          "Tus documentos: los archivos que subes (PDFs, imágenes y facturas electrónicas XML; a las imágenes se les quitan los metadatos, incluida la ubicación, antes de leerlas), que se borran apenas se procesan, y los datos extraídos de ellos. En modo solo procesar esos datos se conservan 1 hora y nunca se escriben en una base de datos; solo se guardan si eliges guardarlos en tu historial.",
          "Uso y pagos: las páginas que procesas y cuándo, tu plan, los paquetes de páginas que compras y, de cada pago, el estado, el monto, la moneda y los números de referencia de PayPal. Los datos de tu tarjeta se ingresan en la ventana de PayPal y nunca llegan a nuestros servidores.",
          "Datos técnicos: tu dirección IP, usada por poco tiempo (hasta una hora) en la memoria del servidor para limitar intentos de acceso y evitar abusos, y que no se guarda en nuestra base de datos; y los registros estándar de solicitudes de nuestros servidores, conservados por seguridad y para resolver problemas.",
        ],
      },
      {
        title: "3. Documentos e inteligencia artificial",
        paragraphs: [
          "Para extraer los datos, el texto de tus documentos se envía a la API de Gemini de Google. No usamos tus documentos para entrenar modelos de IA. Google procesa el texto bajo sus propios términos y, según el nivel de servicio, puede usarlo para mejorar sus productos.",
          "Te pedimos no subir documentos con información sensible que no necesites procesar (por ejemplo datos de salud o contraseñas), y subir datos de otras personas solo cuando tengas derecho a hacerlo.",
        ],
      },
      {
        title: "4. Cookies y almacenamiento del navegador",
        paragraphs: [
          "No usamos cookies de publicidad ni de analítica, y no te seguimos por otros sitios. Extracta solo usa lo necesario para funcionar:",
        ],
        bullets: [
          "una cookie de sesión que mantiene tu sesión iniciada (y otra aparte para el panel de administración del dueño, que nunca se crea para visitantes);",
          "tu tema claro u oscuro y tu idioma, guardados en tu navegador;",
          "tu lote actual de resultados, guardado en tu navegador para que no se pierda al recargar;",
          "cookies que PayPal crea en su ventana de pago para prevenir fraudes.",
        ],
        after: [
          "Como son estrictamente necesarias, no pedimos consentimiento de cookies.",
          "Para saber cuántas personas visitan el sitio, contamos visitantes únicos sin cookies: tu dirección IP y tu navegador se convierten en un código irreversible que solo suma uno a un total diario. Solo se guardan los totales (hasta 400 días); nunca guardamos tu dirección ni ese código, y no podemos saber quién visitó.",
        ],
      },
      {
        title: "5. Para qué usamos tus datos",
        paragraphs: [],
        bullets: [
          "Para entregarte el servicio que pediste: tu cuenta, el procesamiento de tus documentos, tu plan y tus pagos.",
          "Para enviarte emails del servicio: confirmación de email, cambio de contraseña y avisos de seguridad. No enviamos publicidad.",
          "Para cumplir obligaciones legales, como llevar registros contables y tributarios.",
          "Para mantener el servicio seguro y evitar abusos, que es nuestro interés legítimo.",
        ],
        after: ["Nunca vendemos tus datos ni los usamos para publicidad."],
      },
      {
        title: "6. Con quién los compartimos",
        paragraphs: ["Solo compartimos datos con los proveedores que hacen funcionar Extracta, y solo lo que cada uno necesita:"],
        bullets: [
          "Google (API de Gemini): extraer los datos de tus documentos; y Google Sign-In, solo si lo usas.",
          "Supabase: alojamiento de la base de datos.",
          "PayPal: procesamiento de pagos.",
          "Un proveedor de envío de emails: enviar los emails del servicio.",
          "Nuestro proveedor de hosting de servidores.",
        ],
        after: ["También podemos revelar datos cuando lo exija la ley o un tribunal o autoridad pública."],
      },
      {
        title: "7. Transferencias internacionales",
        paragraphs: [
          "Estos proveedores pueden almacenar y procesar datos fuera de Chile, incluidos Estados Unidos y la Unión Europea. Aplican sus propias medidas de seguridad y garantías contractuales para estas transferencias.",
        ],
      },
      {
        title: "8. Cuánto tiempo los guardamos",
        paragraphs: [],
        bullets: [
          "Archivos subidos: se borran apenas se procesan; los que quedan por un error se eliminan en pocas horas.",
          "Resultados de solo procesar: 1 hora.",
          "Documentos guardados: hasta que los borres o cierres tu cuenta.",
          "Datos de la cuenta: mientras esté activa, y se borran cuando nos pidas cerrarla, salvo lo que la ley nos obligue a conservar.",
          "Registros de pago: el tiempo que exija la ley tributaria y contable.",
        ],
      },
      {
        title: "9. Tus derechos",
        paragraphs: ["Puedes pedirnos en cualquier momento:"],
        bullets: [
          "acceder a los datos personales que tenemos sobre ti;",
          "corregir datos incorrectos o incompletos;",
          "borrar tus datos, cuando la ley no nos obligue a conservarlos;",
          "oponerte a su uso o limitarlo;",
          "recibir una copia en un formato portable (también puedes exportar tus documentos a Excel, CSV o JSON tú mismo).",
        ],
        after: [
          `Escribe a ${E} desde el email de tu cuenta. Respondemos dentro de 30 días. También puedes reclamar ante la autoridad de protección de datos o del consumidor de tu país.`,
          "Para eliminar tu cuenta y sus datos tú mismo, usa el botón de la página de tu cuenta o el formulario de /delete-account; las solicitudes enviadas por email se completan dentro de 48 horas.",
        ],
      },
      {
        title: "10. Seguridad",
        paragraphs: [
          "Los datos viajan por conexiones cifradas (HTTPS), las contraseñas se guardan como hashes lentos con sal, cada cuenta solo puede llegar a sus propios datos en la base de datos y los datos de tarjeta los maneja solo PayPal. Ningún sistema es completamente seguro, pero tomamos medidas razonables para proteger tus datos y te avisaremos como exija la ley si un incidente los afecta.",
        ],
      },
      {
        title: "11. Menores de edad",
        paragraphs: ["Extracta está dirigido a adultos y empresas. No recopilamos a sabiendas datos de menores de 18 años."],
      },
      {
        title: "12. Cambios a esta política",
        paragraphs: ["Podemos actualizar esta política. La fecha al inicio indica la versión vigente, y los cambios importantes se destacarán en el sitio o se enviarán por email."],
      },
    ],
  },
};

export const LEGAL = { terms, privacy };
