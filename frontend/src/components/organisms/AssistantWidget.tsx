import { useCallback, useEffect, useRef, useState } from 'react';
import { RetellWebClient } from 'retell-client-js-sdk';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { ASSISTANT_ACCESS_CODE, ASSISTANT_API_URL } from '../../data/assistantApi';
import './AssistantWidget.css';

type CallPhase = 'idle' | 'connecting' | 'listening' | 'speaking';
type TranscriptMessage = { role: 'user' | 'agent'; content: string };
type AssistantProduct = {
  id: number;
  name: string;
  priceUsd: number | null;
  discountPct: number | null;
  rating: number | null;
};
type AssistantScreenAction = {
  key: string;
  path: string;
};
type QueuedScreenAction = {
  id: number;
  tipo:
    | 'catalogo'
    | 'producto'
    | 'navegar'
    | 'mostrar_productos'
    | 'abrir_producto'
    | 'ir_a';
  ruta: string;
  ids?: number[];
  consulta?: string;
  destino?: string;
  producto_id?: number;
};
type CreateCallResponse = {
  access_token: string;
  call_id: string;
  transport?: 'livekit' | 'gateway';
  ice_servers?: RTCIceServer[];
};

function recordFrom(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? value as Record<string, unknown> : null;
}

function optionalNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function searchResultsFromUpdate(update: unknown): {
  products: AssistantProduct[];
  searched: boolean;
} {
  const event = recordFrom(update);
  const transcript = event?.transcript;
  if (!Array.isArray(transcript)) return { products: [], searched: false };

  for (const utterance of [...transcript].reverse()) {
    const message = recordFrom(utterance);
    if (message?.role !== 'tool_call_result' || typeof message.content !== 'string') continue;

    let result: unknown;
    try {
      result = JSON.parse(message.content);
    } catch {
      continue;
    }

    const payload = recordFrom(result);
    if (!payload || !Array.isArray(payload.resultados)) continue;

    const products: AssistantProduct[] = [];
    for (const item of payload.resultados) {
      const product = recordFrom(item);
      const id = optionalNumber(product?.id);
      if (!id || !Number.isInteger(id) || typeof product?.nombre !== 'string') continue;
      products.push({
        id,
        name: product.nombre,
        priceUsd: optionalNumber(product.precio_usd),
        discountPct: optionalNumber(product.descuento_pct),
        rating: optionalNumber(product.calificacion),
      });
    }

    return {
      products: [...new Map(products.map((product) => [product.id, product])).values()].slice(0, 5),
      searched: true,
    };
  }

  return { products: [], searched: false };
}

function transcriptFromUpdate(update: unknown): TranscriptMessage[] {
  const transcript = recordFrom(update)?.transcript;
  if (!Array.isArray(transcript)) return [];

  return transcript.flatMap((utterance) => {
    const message = recordFrom(utterance);
    if (
      (message?.role !== 'user' && message?.role !== 'agent') ||
      typeof message.content !== 'string' ||
      !message.content.trim()
    ) {
      return [];
    }
    const role: TranscriptMessage['role'] = message.role === 'agent' ? 'agent' : 'user';
    return [{ role, content: message.content }];
  }).slice(-8);
}

function latestUserQuery(update: unknown): string {
  const transcript = recordFrom(update)?.transcript;
  if (!Array.isArray(transcript)) return '';
  for (const utterance of [...transcript].reverse()) {
    const message = recordFrom(utterance);
    if (message?.role === 'user' && typeof message.content === 'string') {
      return message.content.trim();
    }
  }
  return '';
}

function screenActionFromUpdate(update: unknown): AssistantScreenAction | null {
  const transcript = recordFrom(update)?.transcript;
  if (!Array.isArray(transcript)) return null;

  for (let index = transcript.length - 1; index >= 0; index -= 1) {
    const message = recordFrom(transcript[index]);
    if (message?.role !== 'tool_call_result' || typeof message.content !== 'string') continue;

    let payload: Record<string, unknown> | null;
    try {
      payload = recordFrom(JSON.parse(message.content));
    } catch {
      continue;
    }
    if (!payload) continue;

    const key = typeof message.tool_call_id === 'string'
      ? message.tool_call_id
      : `tool-result-${index}`;
    if (payload.accion === 'navegar' && typeof payload.destino === 'string') {
      const routes: Record<string, string> = {
        inicio: '/',
        catalogo: '/catalogo',
        metricas: '/admin/dashboard',
        perfil: '/perfil',
      };
      if (payload.destino === 'producto') {
        const id = optionalNumber(payload.producto_id);
        if (id && Number.isInteger(id) && id > 0) {
          return { key, path: `/producto/${id}` };
        }
        continue;
      }
      const path = routes[payload.destino];
      if (path) return { key, path };
      continue;
    }

    if (Array.isArray(payload.resultados)) {
      const productIds = payload.resultados.flatMap((item) => {
        const product = recordFrom(item);
        const id = optionalNumber(product?.id);
        return id && Number.isInteger(id) && id > 0 ? [id] : [];
      });
      const params = new URLSearchParams();
      params.set('ids', [...new Set(productIds)].join(','));
      const query = latestUserQuery(update);
      if (query) params.set('consulta', query);
      return {
        key,
        path: `/catalogo?${params.toString()}`,
      };
    }

    const detailId = optionalNumber(payload.id);
    if (typeof payload.caracteristicas === 'string' && detailId && Number.isInteger(detailId) && detailId > 0) {
      return { key, path: `/producto/${detailId}` };
    }
  }

  return null;
}

function screenPathFromQueuedAction(action: QueuedScreenAction): string | null {
  if (action.tipo === 'catalogo' || action.tipo === 'mostrar_productos') {
    const ids = Array.isArray(action.ids)
      ? action.ids.filter((id) => Number.isInteger(id) && id > 0)
      : [];
    const params = new URLSearchParams();
    params.set('ids', ids.join(','));
    if (action.consulta) params.set('consulta', action.consulta);
    return `/catalogo?${params.toString()}`;
  }

  if (action.tipo === 'producto' || action.tipo === 'abrir_producto') {
    const id = optionalNumber(action.producto_id);
    return id && Number.isInteger(id) && id > 0 ? `/producto/${id}` : null;
  }

  const sectionPaths: Record<string, string> = {
    inicio: '/',
    catalogo: '/catalogo',
    metricas: '/admin/dashboard',
    perfil: '/perfil',
  };
  if (action.destino === 'producto') {
    const id = optionalNumber(action.producto_id);
    return id && Number.isInteger(id) && id > 0 ? `/producto/${id}` : null;
  }
  return action.destino ? sectionPaths[action.destino] ?? null : null;
}

function errorName(error: unknown): string {
  return error instanceof Error ? error.name : 'Error desconocido';
}

export default function AssistantWidget() {
  const { ready, user } = useAuth();
  if (!ready || !user) return null;
  return <AuthenticatedAssistantWidget key={user.id} />;
}

function AuthenticatedAssistantWidget() {
  const navigate = useNavigate();
  const clientRef = useRef<RetellWebClient | null>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [accessCode, setAccessCode] = useState(ASSISTANT_ACCESS_CODE);
  const [phase, setPhase] = useState<CallPhase>('idle');
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [status, setStatus] = useState('Pulsa el micrófono y busca productos por voz.');
  const [isError, setIsError] = useState(false);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [searchResults, setSearchResults] = useState<AssistantProduct[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [technicalLog, setTechnicalLog] = useState<string[]>([]);
  const [copyStatus, setCopyStatus] = useState('');
  const phaseRef = useRef<CallPhase>('idle');
  const mountedRef = useRef(false);
  const attemptRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const toggleButtonRef = useRef<HTMLButtonElement>(null);
  const panelWasOpenRef = useRef(false);
  const lastScreenActionRef = useRef('');

  const recordTechnicalEvent = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setTechnicalLog((current) => [...current.slice(-7), `[${timestamp}] ${message}`]);
  }, []);

  const updatePhase = useCallback((nextPhase: CallPhase) => {
    phaseRef.current = nextPhase;
    setPhase(nextPhase);
  }, []);

  useEffect(() => {
    if (clientRef.current === null) clientRef.current = new RetellWebClient();
    const client = clientRef.current;
    mountedRef.current = true;

    client.on('call_started', () => {
      if (!mountedRef.current) return;
      updatePhase('listening');
      setIsError(false);
      setStatus('Te escucho.');
      recordTechnicalEvent('Llamada conectada.');
    });
    client.on('call_ready', () => {
      if (!mountedRef.current) return;
      updatePhase('listening');
      setIsError(false);
      setStatus('Te escucho.');
      recordTechnicalEvent('Audio listo.');
    });
    client.on('call_ended', () => {
      if (!mountedRef.current) return;
      setActiveCallId(null);
      updatePhase('idle');
      setStatus('Llamada terminada. Puedes iniciar otra.');
      setIsError(false);
      recordTechnicalEvent('Llamada terminada.');
    });
    client.on('agent_start_talking', () => {
      if (!mountedRef.current) return;
      updatePhase('speaking');
      setStatus('Vortex está hablando…');
      setIsError(false);
    });
    client.on('agent_stop_talking', () => {
      if (!mountedRef.current) return;
      if (phaseRef.current !== 'idle') {
        updatePhase('listening');
        setStatus('Te escucho.');
      }
    });
    client.on('update', (update: unknown) => {
      if (!mountedRef.current) return;
      setMessages(transcriptFromUpdate(update));
      const search = searchResultsFromUpdate(update);
      if (search.searched) {
        setHasSearched(true);
        setSearchResults(search.products);
      }
      const screenAction = screenActionFromUpdate(update);
      if (screenAction && screenAction.key !== lastScreenActionRef.current) {
        lastScreenActionRef.current = screenAction.key;
        navigate(screenAction.path);
      }
    });
    client.on('error', (error: unknown) => {
      if (!mountedRef.current) return;
      recordTechnicalEvent(`Error del SDK (${errorName(error)}).`);
      try {
        client.stopCall();
      } finally {
        setActiveCallId(null);
        updatePhase('idle');
        setStatus('No se pudo mantener la llamada. Revisa los detalles técnicos.');
        setIsError(true);
      }
    });

    return () => {
      mountedRef.current = false;
      attemptRef.current += 1;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      if (phaseRef.current !== 'idle') client.stopCall();
      client.removeAllListeners();
    };
  }, [navigate, recordTechnicalEvent, updatePhase]);

  useEffect(() => {
    if (!activeCallId) return;
    const callId = activeCallId;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    let cursor = 0;
    let hasLoggedPollError = false;

    async function pollActions() {
      try {
        const response = await fetch(
          `${ASSISTANT_API_URL}/api/acciones/${encodeURIComponent(callId)}?desde=${cursor}`,
          { signal: controller.signal },
        );
        if (!response.ok) {
          throw new Error(`El puente respondió HTTP ${response.status} al consultar acciones.`);
        }

        const payload = (await response.json()) as {
          acciones?: QueuedScreenAction[];
          ultimo?: number;
        };
        hasLoggedPollError = false;
        const acciones = Array.isArray(payload.acciones) ? payload.acciones : [];
        if (typeof payload.ultimo === 'number' && Number.isInteger(payload.ultimo)) {
          cursor = Math.max(cursor, payload.ultimo);
        } else if (acciones.length > 0) {
          cursor = Math.max(cursor, ...acciones.map((accion) => accion.id));
        }

        const paths = acciones
          .map(screenPathFromQueuedAction)
          .filter((path): path is string => path !== null);
        const latestPath = paths.at(-1);
        if (latestPath) navigate(latestPath);
      } catch (error) {
        if (
          !cancelled &&
          !hasLoggedPollError &&
          !(error instanceof DOMException && error.name === 'AbortError')
        ) {
          hasLoggedPollError = true;
          recordTechnicalEvent(
            error instanceof Error ? error.message : 'No se pudieron consultar acciones de pantalla.',
          );
        }
      } finally {
        if (!cancelled) timer = setTimeout(() => void pollActions(), 1000);
      }
    }

    void pollActions();
    return () => {
      cancelled = true;
      controller.abort();
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [activeCallId, navigate, recordTechnicalEvent]);

  useEffect(() => {
    if (isOpen) {
      closeButtonRef.current?.focus();
      panelWasOpenRef.current = true;
    } else if (panelWasOpenRef.current) {
      toggleButtonRef.current?.focus();
      panelWasOpenRef.current = false;
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false);
    }

    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isOpen]);

  async function checkMicrophone(): Promise<string | null> {
    if (!navigator.mediaDevices?.getUserMedia) {
      return 'El navegador no permite acceder al micrófono. Usa HTTPS o localhost.';
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      recordTechnicalEvent('Micrófono disponible.');
      return null;
    } catch (error) {
      const name = errorName(error);
      recordTechnicalEvent(`Micrófono no disponible (${name}).`);
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        return 'El navegador bloqueó el micrófono. Permite su uso en los permisos del sitio e inténtalo de nuevo.';
      }
      if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        return 'No se encontró ningún micrófono conectado.';
      }
      return 'No se pudo acceder al micrófono. Revisa los permisos y vuelve a intentarlo.';
    }
  }

  async function startCall() {
    const code = accessCode.trim();
    if (!code) {
      setStatus('Escribe la clave de acceso.');
      setIsError(true);
      return;
    }

    const attempt = ++attemptRef.current;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    updatePhase('connecting');
    setStatus('Conectando…');
    setIsError(false);
    setMessages([]);
    setSearchResults([]);
    setHasSearched(false);
    setTechnicalLog([]);
    lastScreenActionRef.current = '';

    const microphoneProblem = await checkMicrophone();
    if (!mountedRef.current || attempt !== attemptRef.current) return;
    if (microphoneProblem) {
      updatePhase('idle');
      setStatus(microphoneProblem);
      setIsError(true);
      return;
    }

    try {
      const response = await fetch(`${ASSISTANT_API_URL}/api/crear-llamada`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codigo: code }),
        signal: controller.signal,
      });

      if (!mountedRef.current || attempt !== attemptRef.current) return;

      const payload = (await response.json().catch(() => ({}))) as {
        detail?: unknown;
      } & Partial<CreateCallResponse>;

      if (!response.ok) {
        const detail = typeof payload.detail === 'string' ? payload.detail : '';
        recordTechnicalEvent(`El puente respondió HTTP ${response.status}.`);
        if (response.status === 401) {
          throw new Error(detail || 'La clave de acceso es incorrecta.');
        }
        if (response.status === 429) {
          throw new Error(detail || 'Se alcanzó el límite de llamadas. Inténtalo más tarde.');
        }
        if (response.status === 502) {
          throw new Error(detail || 'El servicio de voz no está disponible por ahora.');
        }
        throw new Error(detail || `No se pudo iniciar la llamada (HTTP ${response.status}).`);
      }

      if (
        typeof payload.access_token !== 'string' ||
        typeof payload.call_id !== 'string'
      ) {
        throw new Error('El puente devolvió una respuesta de llamada incompleta.');
      }

      recordTechnicalEvent('Solicitud de llamada aceptada por el puente.');
      setActiveCallId(payload.call_id);
      const client = clientRef.current;
      if (!client) throw new Error('El cliente de voz todavía no está listo.');

      await client.startCall({
        accessToken: payload.access_token,
        callId: payload.call_id,
        transport: payload.transport,
        iceServers: payload.ice_servers,
      });

      if (!mountedRef.current || attempt !== attemptRef.current) client.stopCall();
    } catch (error) {
      if (!mountedRef.current || attempt !== attemptRef.current) return;
      if (error instanceof DOMException && error.name === 'AbortError') return;

      recordTechnicalEvent(`No se pudo iniciar la llamada (${errorName(error)}).`);
      setActiveCallId(null);
      updatePhase('idle');
      setStatus(error instanceof Error ? error.message : 'No se pudo iniciar la llamada.');
      setIsError(true);
    } finally {
      if (attempt === attemptRef.current) abortControllerRef.current = null;
    }
  }

  function endCall() {
    attemptRef.current += 1;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setActiveCallId(null);
    clientRef.current?.stopCall();
    updatePhase('idle');
    setStatus('Llamada terminada. Puedes iniciar otra.');
    setIsError(false);
  }

  async function handleMicrophoneClick() {
    if (phase === 'connecting') return;
    if (phase !== 'idle') {
      endCall();
      return;
    }
    await startCall();
  }

  async function copyAccessCode() {
    const code = accessCode.trim();
    if (!code) {
      setCopyStatus('No hay una clave configurada.');
      return;
    }
    try {
      await navigator.clipboard.writeText(code);
      setCopyStatus('Clave copiada.');
    } catch {
      setCopyStatus('No se pudo copiar la clave desde este navegador.');
    }
  }

  return (
    <div className="assistant-widget">
      {isOpen ? (
        <section
          id="assistant-widget-panel"
          className="assistant-widget__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="assistant-widget-title"
        >
          <header className="assistant-widget__header">
            <h2 className="assistant-widget__title" id="assistant-widget-title">
              Vortex · asistente de voz
            </h2>
            <button
              className="assistant-widget__close"
              type="button"
              aria-label="Cerrar panel del asistente"
              onClick={() => setIsOpen(false)}
              ref={closeButtonRef}
            >
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <div className="assistant-widget__content">
            <div className="assistant-widget__access">
              <div className="assistant-widget__access-heading">
                <span>Clave de acceso</span>
                <button
                  className="assistant-widget__copy"
                  type="button"
                  onClick={() => void copyAccessCode()}
                  disabled={!accessCode.trim()}
                >
                  Copiar
                </button>
              </div>
              <input
                className="assistant-widget__input"
                aria-label="Clave de acceso editable"
                autoComplete="off"
                value={accessCode}
                onChange={(event) => setAccessCode(event.target.value)}
              />
              {copyStatus ? <span className="assistant-widget__copy-status">{copyStatus}</span> : null}
            </div>

            <button
              className={`assistant-widget__microphone${phase === 'speaking' ? ' assistant-widget__microphone--speaking' : ''}${phase === 'listening' || phase === 'speaking' ? ' assistant-widget__microphone--active' : ''}`}
              type="button"
              onClick={() => void handleMicrophoneClick()}
              disabled={phase === 'connecting'}
              aria-label={
                phase === 'connecting'
                  ? 'Conectando con Vortex'
                  : phase === 'idle'
                    ? 'Iniciar llamada con Vortex'
                    : 'Terminar llamada'
              }
            >
              {phase === 'listening' || phase === 'speaking' ? (
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <rect x="9" y="3" width="6" height="12" rx="3" />
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
                </svg>
              )}
            </button>
            <p
              className={`assistant-widget__status${isError ? ' assistant-widget__status--error' : ''}`}
              role="status"
              aria-live="polite"
            >
              {status}
            </p>

            {phase !== 'idle' ? (
              <button
                className="assistant-widget__end-call"
                type="button"
                onClick={endCall}
              >
                Terminar llamada
              </button>
            ) : null}

            <ol className="assistant-widget__transcript" aria-label="Transcripción en vivo" aria-live="polite">
              {messages.map((message, index) => (
                <li
                  className={`assistant-widget__message${message.role === 'agent' ? ' assistant-widget__message--agent' : ''}`}
                  key={`${message.role}-${index}`}
                >
                  <span className="assistant-widget__speaker">
                    {message.role === 'agent' ? 'Vortex' : 'Tú'}
                  </span>
                  <span>{message.content}</span>
                </li>
              ))}
            </ol>

            {hasSearched ? (
              <section className="assistant-widget__results" aria-live="polite" aria-label="Productos encontrados">
                <h3 className="assistant-widget__results-title">
                  {searchResults.length ? 'Productos encontrados' : 'No encontré productos con esos criterios'}
                </h3>
                {searchResults.map((product) => (
                  <article className="assistant-widget__result" key={product.id}>
                    <Link className="assistant-widget__result-link" to={`/producto/${product.id}`}>
                      {product.name}
                    </Link>
                    <div className="assistant-widget__result-meta">
                      {product.priceUsd !== null ? (
                        <span>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(product.priceUsd)}</span>
                      ) : null}
                      {product.discountPct !== null && product.discountPct > 0 ? (
                        <span>{product.discountPct}% descuento</span>
                      ) : null}
                      {product.rating !== null ? <span>★ {product.rating.toFixed(1)}</span> : null}
                    </div>
                  </article>
                ))}
              </section>
            ) : null}

            <Link className="assistant-widget__catalog-link" to="/catalogo">
              Explorar catálogo completo
            </Link>

            <details className="assistant-widget__details">
              <summary>Detalles técnicos</summary>
              <pre>{technicalLog.length ? technicalLog.join('\n') : 'Aún no hay eventos técnicos.'}</pre>
            </details>
          </div>
        </section>
      ) : null}

      <button
        className="assistant-widget__toggle"
        type="button"
        aria-controls="assistant-widget-panel"
        aria-label={isOpen ? 'Cerrar asistente de voz' : 'Abrir asistente de voz'}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        ref={toggleButtonRef}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 5.75A2.75 2.75 0 0 1 6.75 3h10.5A2.75 2.75 0 0 1 20 5.75v7.5A2.75 2.75 0 0 1 17.25 16H11l-5.5 4v-4.1A2.75 2.75 0 0 1 4 13.25z" />
          <path d="M8 9.5h8M8 12.5h5" />
        </svg>
      </button>
    </div>
  );
}
