// Android uses its local native backend; desktop uses the Python HTTP API.
const nativeRequests = new Map();
let nativeRequestId = 0;
window.MDZNativeResult = (id, data) => {
  const request = nativeRequests.get(id);
  if (!request) return;
  clearTimeout(request.timeout);
  nativeRequests.delete(id);
  request.resolve({json: async () => data});
};
function mdzFetch(path, options = {}) {
  if (!window.MDZAndroid) return fetch(path, options);
  return new Promise((resolve, reject) => {
    const id = ++nativeRequestId;
    const timeout = setTimeout(() => {
      nativeRequests.delete(id);
      reject(new Error('Request timed out'));
    }, 20000);
    nativeRequests.set(id, {resolve, timeout});
    try {
      window.MDZAndroid.request(id, path, options.method || 'GET', options.body || '');
    } catch (error) {
      clearTimeout(timeout);
      nativeRequests.delete(id);
      reject(error);
    }
  });
}
