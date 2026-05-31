import { useEffect, useRef, useState } from "react";
import axios from "axios";

function formatSearchError(error) {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;

    if (status === 404) {
        return "Search API not found. Restart the backend (uvicorn main:app --reload).";
    }
    if (status === 502 && detail) {
        return String(detail);
    }
    if (typeof detail === "string") {
        return detail;
    }
    if (!error?.response) {
        return "Cannot reach the API. Start the backend on port 8000.";
    }
    return "Search failed. Try again in a moment.";
}

export default function AddressSearch({ apiUrl, onSelect, disabled }) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [hasSearched, setHasSearched] = useState(false);
    const debounceRef = useRef(null);
    const requestIdRef = useRef(0);

    const handleQueryChange = (value) => {
        setQuery(value);
        setHasSearched(false);
        if (value.trim().length < 3) {
            setResults([]);
            setError("");
        }
    };

    useEffect(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        const trimmed = query.trim();
        if (trimmed.length < 3) {
            return;
        }

        debounceRef.current = setTimeout(async () => {
            const requestId = ++requestIdRef.current;
            setLoading(true);
            setError("");
            try {
                const response = await axios.get(`${apiUrl}/geocode`, {
                    params: { q: trimmed },
                    timeout: 15000,
                });
                if (requestId !== requestIdRef.current) {
                    return;
                }
                setResults(response.data);
                setHasSearched(true);
            } catch (err) {
                if (requestId !== requestIdRef.current) {
                    return;
                }
                setResults([]);
                setHasSearched(true);
                setError(formatSearchError(err));
            } finally {
                if (requestId === requestIdRef.current) {
                    setLoading(false);
                }
            }
        }, 400);

        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        };
    }, [query, apiUrl]);

    const handleSelect = (item) => {
        onSelect([item.lat, item.lon], item.display_name);
        setQuery("");
        setResults([]);
        setHasSearched(false);
        setError("");
    };

    const showNoResults = hasSearched && !loading && !error && results.length === 0 && query.trim().length >= 3;

    return (
        <div className="search-block">
            <label className="sr-only" htmlFor="address-search">
                Search address
            </label>
            <input
                id="address-search"
                type="text"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                disabled={disabled}
                placeholder="Search address or place…"
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 disabled:opacity-60"
                autoComplete="off"
            />
            {loading && <p className="mt-1 text-xs text-slate-500">Searching…</p>}
            {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
            {showNoResults && (
                <p className="mt-1 text-xs text-slate-500">No places found for &ldquo;{query.trim()}&rdquo;</p>
            )}
            {results.length > 0 && (
                <ul className="search-results" role="listbox">
                    {results.map((item) => (
                        <li key={`${item.lat}-${item.lon}-${item.display_name}`} role="option">
                            <button
                                type="button"
                                onClick={() => handleSelect(item)}
                                className="search-result-btn"
                            >
                                {item.display_name}
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
