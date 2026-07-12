// louke web client - minimal JSON client for the six v0.11-001 sub-apps.
//
// Public surface (interfaces.md §7.1): window.LoukeClient with six namespaces
// (opencode / intent / wiki / backlog / files / tasks), each calling the locked
// HTTP endpoints over same-origin fetch. No fixtures, no mock fallback.
//
// Failure contract (interfaces.md §7.1):
//   - locked non-2xx JSON  -> rejected {status, error_code, message, detail}
//   - network / non-JSON   -> rejected {status: 0, error_code: "CLIENT_REQUEST_FAILED", message}
(function (global) {
  'use strict';

  async function _jsonFetch(method, url, body) {
    /** Perform a same-origin JSON fetch and return parsed data.
     *
     * Resolves with the parsed JSON body (or null for 204). Rejects with an
     * Error carrying {status, error_code, message, detail?} for locked
     * non-2xx responses, or {status:0, error_code:"CLIENT_REQUEST_FAILED"}
     * for network/non-JSON failures (interfaces.md §7.1).
     */
    var opts = {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
    }
    var resp;
    try {
      resp = await fetch(url, opts);
    } catch (networkErr) {
      var netErr = new Error('network request failed');
      netErr.status = 0;
      netErr.error_code = 'CLIENT_REQUEST_FAILED';
      netErr.detail = String(networkErr);
      throw netErr;
    }
    var data = null;
    if (resp.status !== 204) {
      try {
        data = await resp.json();
      } catch (parseErr) {
        var badErr = new Error('non-JSON response');
        badErr.status = resp.status;
        badErr.error_code = 'CLIENT_REQUEST_FAILED';
        badErr.detail = String(parseErr);
        throw badErr;
      }
    }
    if (!resp.ok) {
      var err = new Error(
        data && data.message ? data.message : 'HTTP ' + resp.status
      );
      err.status = resp.status;
      err.error_code = data && data.error_code;
      if (data && data.detail !== undefined) {
        err.detail = data.detail;
      }
      throw err;
    }
    return data;
  }

  function _qs(params) {
    /** Build a query string from {k:v}, skipping undefined/null/empty. */
    var parts = [];
    if (!params) return '';
    for (var k in params) {
      if (!Object.prototype.hasOwnProperty.call(params, k)) continue;
      var v = params[k];
      if (v === undefined || v === null || v === '') continue;
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
    }
    return parts.length ? '?' + parts.join('&') : '';
  }

  var LoukeClient = {
    // OpenCode instances (FR-0001): create / list / stop / send / messages.
    opencode: {
      create: function () {
        return _jsonFetch('POST', '/api/opencode/instances', {});
      },
      list: function () {
        return _jsonFetch('GET', '/api/opencode/instances');
      },
      stop: function (id) {
        return _jsonFetch(
          'DELETE',
          '/api/opencode/instances' + _qs({ id: id })
        );
      },
      send: function (instanceId, content) {
        return _jsonFetch(
          'POST',
          '/api/opencode/instances/' + encodeURIComponent(instanceId) + '/messages',
          { content: content }
        );
      },
      messages: function (instanceId, after) {
        return _jsonFetch(
          'GET',
          '/api/opencode/instances/' +
            encodeURIComponent(instanceId) +
            '/messages' +
            _qs({ after: after })
        );
      },
    },

    // Intent classifier (FR-0201): route -> IntentRouteResult.
    intent: {
      route: function (input, selection, confirmation) {
        var body = { input: input };
        if (selection !== undefined) body.selection = selection;
        if (confirmation !== undefined) body.confirmation = confirmation;
        return _jsonFetch('POST', '/api/intent/route', body);
      },
    },

    // Traceable wiki (FR-0301): get canonical page / build.
    wiki: {
      get: function (type, includeContent) {
        var ic = includeContent === false ? false : true;
        return _jsonFetch(
          'GET',
          '/api/wiki/' + encodeURIComponent(type) + _qs({ include_content: ic ? '' : 'false' })
        );
      },
      build: function (type, trigger) {
        return _jsonFetch(
          'PUT',
          '/api/wiki/' + encodeURIComponent(type),
          { trigger: trigger || 'manual' }
        );
      },
    },

    // Backlog (FR-0601): list / create / start (delete with action).
    backlog: {
      list: function () {
        return _jsonFetch('GET', '/api/backlog');
      },
      create: function (story) {
        return _jsonFetch('POST', '/api/backlog', { story: story });
      },
      start: function (id) {
        return _jsonFetch('DELETE', '/api/backlog', {
          id: id,
          action: 'start_development',
        });
      },
    },

    // Files (FR-0701/0801): list (tree/changes/documents/content) / content /
    // diff / save. The locked single GET endpoint dispatches by view param.
    files: {
      list: function (view, path, approved) {
        return _jsonFetch(
          'GET',
          '/api/files' + _qs({ view: view, path: path, approved: approved })
        );
      },
      content: function (path, approved) {
        return _jsonFetch(
          'GET',
          '/api/files' + _qs({ view: 'content', path: path, approved: approved })
        );
      },
      diff: function (path) {
        return _jsonFetch(
          'GET',
          '/api/files/diff' + _qs({ path: path })
        );
      },
      save: function (path, content, revision) {
        var body = { content: content };
        if (revision !== undefined) body.revision = revision;
        return _jsonFetch(
          'PUT',
          '/api/files/' + encodeURIComponent(path),
          body
        );
      },
    },

    // Tasks (FR-0501): get current state / toggle one task.
    tasks: {
      get: function (frId, documentPath) {
        return _jsonFetch(
          'GET',
          '/api/tasks/' + encodeURIComponent(frId) + _qs({ document_path: documentPath })
        );
      },
      toggle: function (frId, documentPath, task, checked, revision) {
        var body = {
          document_path: documentPath,
          task: task,
          checked: checked,
        };
        if (revision !== undefined) body.revision = revision;
        return _jsonFetch('PATCH', '/api/tasks/' + encodeURIComponent(frId), body);
      },
    },
  };

  global.LoukeClient = LoukeClient;
})(typeof window !== 'undefined' ? window : this);
