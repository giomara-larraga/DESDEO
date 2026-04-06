// NOTE: Supports cases where `content-type` is other than `json`
const getBody = async <T>(c: Response | Request): Promise<T> => {
  // If it's a Response and there is explicitly no content, don't parse anything
  if (c instanceof Response && (c.status === 204 || c.status === 205)) {
    return null as T;
  }

  const contentType = c.headers.get('content-type');
  console.error(`[getBody] contentType: ${contentType}, status: ${c instanceof Response ? c.status : 'N/A'}`);

  if (contentType && contentType.includes('application/json')) {
    // Avoid JSON.parse errors on empty bodies
    const text = await (c as Response).text?.() ?? '';
    console.error(`[getBody] json text length: ${text.length}`);
    if (!text) return null as T;
    const parsed = JSON.parse(text) as T;
    console.error(`[getBody] parsed:`, parsed);
    return parsed;
  }

  if (contentType && contentType.includes('application/pdf')) {
    return (c as Response).blob() as Promise<T>;
  }

  return (c as Response).text() as Promise<T>;
};

// NOTE: Update just base url
const getUrl = (contextUrl: string): string => {
  // Handle relative URLs
  if (contextUrl.startsWith('/')) {
    if (typeof window !== 'undefined') {
      // Browser context - construct full URL with current origin
      return new URL(contextUrl, window.location.origin).toString();
    } else {
      // Server-side context - construct full URL with API backend
      // Remove /api prefix since backend doesn't have it, then add full origin
      const pathWithoutApiPrefix = contextUrl.replace(/^\/api/, '');
      return `http://localhost:8000${pathWithoutApiPrefix}`;
    }
  }
  
  // Absolute URL - parse as-is
  return new URL(contextUrl).toString();
};

const getHeaders = (headers?: HeadersInit): HeadersInit => {
  return {
    ...headers,
    // add headers if needed
  }
};

export const customFetch = async <T>(
  url: string,
  options: (RequestInit & {fetchImpl?: typeof fetch }),
): Promise<T> => {
  const f = options.fetchImpl ?? fetch;

  const requestUrl = getUrl(url);
  const requestHeaders = getHeaders(options.headers);

  const requestInit: RequestInit = {
    ...options,
    headers: requestHeaders,
    credentials: "include",
  };

  const request = new Request(requestUrl, requestInit);
  const retryRequest = request.clone();

  let response = await f(request);

  if (response.status === 401) {
    const refreshUrl = new URL("/refresh", requestUrl).toString();
    const refreshResponse = await f(refreshUrl, {
      method: "POST",
      credentials: "include",
    });

    if (refreshResponse.ok) {
      response = await f(retryRequest);
    }
  }

  const data = await getBody<T>(response);

  return { status: response.status, data, headers: response.headers } as T;
};
