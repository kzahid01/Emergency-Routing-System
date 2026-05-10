import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { createRoot } from "react-dom/client";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

import {
  Activity,
  Ambulance,
  Crosshair,
  Hospital,
  LocateFixed,
  MapPinned,
  Navigation,
  Pause,
  Play,
  Radar,
  Route,
  ShieldAlert,
} from "lucide-react";

import "./styles.css";

/* =========================================
   EMPTY ROUTE
========================================= */

const emptyRoute = {
  algorithm: "Waiting",
  best_responder: null,
  best_hospital: null,
  responder_cost: 0,
  hospital_cost: 0,
  responder_route_coordinates: [],
  hospital_route_coordinates: [],
};

/* =========================================
   BOUNDARY
========================================= */

const g8SectorBoundary = [
  [33.69629712695355, 73.06253033859412],
  [33.69283221269566, 73.0617310860136],
  [33.68534192063541, 73.04742867141482],
  [33.69836200940986, 73.03741698119572],
  [33.70721594269111, 73.05428541723717],
  [33.69633212537474, 73.06257240451936],
  [33.69629712695355, 73.06253033859412],
];

const statusCopy = {
  idle: "Waiting",
  loading: "Finding route",
  success: "Emergency route active",
  error: "Routing failed",
};

/* =========================================
   HELPERS
========================================= */

function toLatLng(points) {
  return points
    .filter(
      (p) =>
        Number.isFinite(p.lat) &&
        Number.isFinite(p.lon)
    )
    .map((p) => [p.lat, p.lon]);
}

function meters(value) {
  if (!Number.isFinite(value)) {
    return "0 m";
  }

  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)} km`;
  }

  return `${Math.round(value)} m`;
}

/* =========================================
   ICONS
========================================= */

function buildVehicleIcon(color = "#2563eb") {
  return L.divIcon({
    className: "vehicle-marker",

    html: `
      <span style="--marker-color:${color}">
        <svg viewBox="0 0 24 24">
          <path d="M6.4 17.5H4.7a1.7 1.7 0 0 1-1.7-1.7v-4.4c0-.9.7-1.6 1.6-1.6h1.1l1.2-3.1c.3-.8 1-1.2 1.8-1.2h5.2c.8 0 1.5.5 1.8 1.2l1.2 3.1h1.2c.9 0 1.6.7 1.6 1.6v4.4c0 .9-.8 1.7-1.7 1.7h-1.5a2.5 2.5 0 0 1-4.9 0H11.3a2.5 2.5 0 0 1-4.9 0Z"/>
        </svg>
      </span>
    `,

    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });
}

function buildEmergencyIcon() {
  return L.divIcon({
    className: "selection-marker from",

    html: `<span><b>!</b></span>`,

    iconSize: [34, 34],
    iconAnchor: [17, 34],
  });
}

function buildHospitalIcon() {
  return L.divIcon({
    className: "selection-marker to",

    html: `<span><b>H</b></span>`,

    iconSize: [34, 34],
    iconAnchor: [17, 34],
  });
}

/* =========================================
   GPS
========================================= */

function useGpsTracking(enabled) {
  const [position, setPosition] =
    useState(null);

  const [error, setError] =
    useState("");

  useEffect(() => {
    if (!enabled) return;

    if (!navigator.geolocation) {
      setError("GPS not supported");
      return;
    }

    const watchId =
      navigator.geolocation.watchPosition(
        (pos) => {
          setPosition({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy:
              pos.coords.accuracy,
          });

          setError("");
        },

        (err) => {
          setError(err.message);
        },

        {
          enableHighAccuracy: true,
          maximumAge: 1000,
          timeout: 10000,
        }
      );

    return () => {
      navigator.geolocation.clearWatch(
        watchId
      );
    };
  }, [enabled]);

  return { position, error };
}

/* =========================================
   MAP
========================================= */

function EmergencyMap({
  routeData,
  livePosition,
  manualPoint,
  playbackIndex,
  followVehicle,
  onMapClick,
}) {
  const mapNodeRef = useRef(null);

  const mapRef = useRef(null);

  const layersRef = useRef({});

  const responderPath = useMemo(
    () =>
      toLatLng(
        routeData.responder_route_coordinates ||
          []
      ),
    [routeData]
  );

  const hospitalPath = useMemo(
    () =>
      toLatLng(
        routeData.hospital_route_coordinates ||
          []
      ),
    [routeData]
  );

  const fullPath = useMemo(
    () => [
      ...responderPath,
      ...hospitalPath.slice(1),
    ],
    [responderPath, hospitalPath]
  );

  /* MAP INIT */

  useEffect(() => {
    if (!mapNodeRef.current || mapRef.current)
      return;

    mapRef.current = L.map(
      mapNodeRef.current,
      {
        zoomControl: false,
      }
    ).setView([33.6963, 73.0525], 14);

    L.control.zoom({
      position: "bottomright",
    }).addTo(mapRef.current);

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution:
          "&copy; OpenStreetMap",
      }
    ).addTo(mapRef.current);

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  /* MAP CLICK */

  useEffect(() => {
    const map = mapRef.current;

    if (!map || !onMapClick) return;

    const clickHandler = (e) => {
      onMapClick({
        lat: e.latlng.lat,
        lon: e.latlng.lng,
      });
    };

    map.on("click", clickHandler);

    return () => {
      map.off("click", clickHandler);
    };
  }, [onMapClick]);

  /* DRAW */

  useEffect(() => {
    const map = mapRef.current;

    if (!map) return;

    Object.values(
      layersRef.current
    ).forEach((layer) => {
      layer?.remove?.();
    });

    layersRef.current = {};

    /* Boundary */

    const boundary = L.polygon(
      g8SectorBoundary,
      {
        color: "#0f172a",
        weight: 2,
        fillOpacity: 0.04,
        dashArray: "8 8",
      }
    ).addTo(map);

    layersRef.current.boundary =
      boundary;

    /* Responder */

    if (responderPath.length > 0) {
      const responderLine = L.polyline(
        responderPath,
        {
          color: "#2563eb",
          weight: 7,
        }
      ).addTo(map);

      layersRef.current.responderLine =
        responderLine;
    }

    /* Hospital */

    if (hospitalPath.length > 0) {
      const hospitalLine = L.polyline(
        hospitalPath,
        {
          color: "#dc2626",
          weight: 7,
        }
      ).addTo(map);

      layersRef.current.hospitalLine =
        hospitalLine;
    }

    /* Vehicle */

    if (fullPath.length > 0) {
      const vehicle = L.marker(
        fullPath[playbackIndex] ||
          fullPath[0],
        {
          icon: buildVehicleIcon(),
          zIndexOffset: 1000,
        }
      ).addTo(map);

      layersRef.current.vehicle =
        vehicle;
    }

    /* GPS */

    if (livePosition) {
      const gpsMarker = L.marker(
        [
          livePosition.lat,
          livePosition.lon,
        ],
        {
          icon: buildEmergencyIcon(),
          zIndexOffset: 1200,
        }
      ).addTo(map);

      layersRef.current.gpsMarker =
        gpsMarker;
    }

    /* Manual */

    if (manualPoint) {
      const manualMarker = L.marker(
        [
          manualPoint.lat,
          manualPoint.lon,
        ],
        {
          icon: buildEmergencyIcon(),
          zIndexOffset: 1300,
        }
      ).addTo(map);

      layersRef.current.manualMarker =
        manualMarker;
    }

    /* Hospital Marker */

    if (hospitalPath.length > 0) {
      const last =
        hospitalPath[
          hospitalPath.length - 1
        ];

      const hospitalMarker = L.marker(
        last,
        {
          icon: buildHospitalIcon(),
        }
      ).addTo(map);

      layersRef.current.hospitalMarker =
        hospitalMarker;
    }

    /* Bounds */

    const bounds =
      L.latLngBounds(g8SectorBoundary);

    fullPath.forEach((p) =>
      bounds.extend(p)
    );

    if (livePosition) {
      bounds.extend([
        livePosition.lat,
        livePosition.lon,
      ]);
    }

    if (manualPoint) {
      bounds.extend([
        manualPoint.lat,
        manualPoint.lon,
      ]);
    }

    if (
      followVehicle &&
      fullPath.length > 0
    ) {
      map.panTo(fullPath[playbackIndex], {
        animate: true,
      });
    } else {
      map.fitBounds(bounds, {
        padding: [40, 40],
        maxZoom: 15,
      });
    }
  }, [
    routeData,
    livePosition,
    manualPoint,
    playbackIndex,
    followVehicle,
    responderPath,
    hospitalPath,
    fullPath,
  ]);

  return (
    <div
      ref={mapNodeRef}
      className="map-canvas"
    />
  );
}

/* =========================================
   APP
========================================= */

function App() {
  const [routeData, setRouteData] =
    useState(emptyRoute);

  const [status, setStatus] =
    useState("idle");

  const [message, setMessage] =
    useState(
      "Choose GPS or click map."
    );

  const [tracking, setTracking] =
    useState(false);

  const [playing, setPlaying] =
    useState(true);

  const [speed, setSpeed] =
    useState(1000);

  const [followVehicle, setFollowVehicle] =
    useState(true);

  const [playbackIndex, setPlaybackIndex] =
    useState(0);

  const [manualPoint, setManualPoint] =
    useState(null);

  const [mode, setMode] =
    useState("manual");

  const [emergencyLevel, setEmergencyLevel] =
    useState("critical");

  const {
    position: livePosition,
    error: gpsError,
  } = useGpsTracking(tracking);

  /* PATHS */

  const responderPath = useMemo(
    () =>
      toLatLng(
        routeData.responder_route_coordinates ||
          []
      ),
    [routeData]
  );

  const hospitalPath = useMemo(
    () =>
      toLatLng(
        routeData.hospital_route_coordinates ||
          []
      ),
    [routeData]
  );

  const fullPath = useMemo(
    () => [
      ...responderPath,
      ...hospitalPath.slice(1),
    ],
    [responderPath, hospitalPath]
  );

  /* GPS AUTO */

  useEffect(() => {
    if (
      mode !== "gps" ||
      !livePosition
    )
      return;

    autoDispatch(
      livePosition.lat,
      livePosition.lon
    );
  }, [livePosition, mode]);

  /* DISPATCH */

  async function autoDispatch(
    lat,
    lon
  ) {
    try {
      setStatus("loading");

      setMessage(
        "Finding nearest ambulance..."
      );

      const response = await fetch(
        "http://localhost:8000/auto-dispatch",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            emergency_lat: lat,
            emergency_lon: lon,
            emergency_level:
              emergencyLevel,
          }),
        }
      );

      const text =
        await response.text();

      if (!text) {
        throw new Error(
          "Backend returned empty response"
        );
      }

      let body;

      try {
        body = JSON.parse(text);
      } catch (err) {
        console.error(
          "INVALID JSON:",
          text
        );

        throw new Error(
          "Backend returned invalid JSON"
        );
      }

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Dispatch failed"
        );
      }

      setRouteData({
        algorithm:
          body.algorithm || "A*",

        best_responder:
          body.best_responder,

        best_hospital:
          body.best_hospital,

        responder_cost:
          body.responder_cost || 0,

        hospital_cost:
          body.hospital_cost || 0,

        responder_route_coordinates:
          body.responder_route_coordinates ||
          [],

        hospital_route_coordinates:
          body.hospital_route_coordinates ||
          [],
      });

      setStatus("success");

      setMessage(
        "Nearest ambulance found successfully."
      );
    } catch (error) {
      console.error(error);

      setStatus("error");

      setMessage(
        error.message ||
          "Routing failed"
      );

      setRouteData({
        algorithm: "Failed",

        best_responder: null,

        best_hospital: null,

        responder_cost: 0,

        hospital_cost: 0,

        responder_route_coordinates:
          [],

        hospital_route_coordinates:
          [],
      });
    }
  }

  /* MANUAL MAP */

  function handleMapClick(point) {
    if (mode !== "manual") return;

    setManualPoint(point);

    autoDispatch(point.lat, point.lon);
  }

  /* PLAYBACK */

  useEffect(() => {
    setPlaybackIndex(0);
  }, [routeData]);

  useEffect(() => {
    if (
      !playing ||
      fullPath.length < 2
    )
      return;

    const timer = setInterval(() => {
      setPlaybackIndex((index) =>
        index + 1 >= fullPath.length
          ? 0
          : index + 1
      );
    }, speed);

    return () => clearInterval(timer);
  }, [playing, speed, fullPath]);

  /* DISTANCE */

  const totalDistance =
    (routeData.responder_cost || 0) +
    (routeData.hospital_cost || 0);

  /* UI */

  return (
    <main className="app-shell">
      <section className="map-stage">
        <EmergencyMap
          routeData={routeData}
          livePosition={
            mode === "gps"
              ? livePosition
              : null
          }
          manualPoint={
            mode === "manual"
              ? manualPoint
              : null
          }
          playbackIndex={playbackIndex}
          followVehicle={followVehicle}
          onMapClick={handleMapClick}
        />

        <div className="topbar">
          <div>
            <p className="eyebrow">
              Emergency AI System
            </p>

            <h1>
              Smart Ambulance Routing
            </h1>
          </div>

          <div
            className={`status-pill ${status}`}
          >
            <Activity size={16} />
            {statusCopy[status]}
          </div>
        </div>
      </section>

      <aside className="control-panel">
        <div className="panel-header">
          <ShieldAlert size={28} />

          <div>
            <p className="eyebrow">
              Dispatch Console
            </p>

            <h2>
              Emergency Controls
            </h2>
          </div>
        </div>

        {/* MODE */}

        <section className="gps-card">
          <div className="section-title">
            <LocateFixed size={20} />
            <h3>Emergency Mode</h3>
          </div>

          <label className="switch-row">
            <input
              type="radio"
              checked={mode === "gps"}
              onChange={() => {
                setMode("gps");
                setTracking(true);
              }}
            />

            GPS Tracking
          </label>

          <label className="switch-row">
            <input
              type="radio"
              checked={
                mode === "manual"
              }
              onChange={() => {
                setMode("manual");
                setTracking(false);
              }}
            />

            Manual Map Click
          </label>
        </section>

        {/* LEVEL */}

        <section className="gps-card">
          <div className="section-title">
            <ShieldAlert size={20} />
            <h3>Emergency Level</h3>
          </div>

          <select
            value={emergencyLevel}
            onChange={(e) =>
              setEmergencyLevel(
                e.target.value
              )
            }
          >
            <option value="low">
              Low
            </option>

            <option value="medium">
              Medium
            </option>

            <option value="critical">
              Critical
            </option>
          </select>
        </section>

        {/* MANUAL */}

        {mode === "manual" && (
          <section className="gps-card">
            <div className="section-title">
              <MapPinned size={20} />
              <h3>
                Manual Emergency
              </h3>
            </div>

            <p className="panel-message">
              Click anywhere on map.
            </p>
          </section>
        )}

        {/* GPS */}

        {mode === "gps" && (
          <section className="gps-card">
            <div className="section-title">
              <LocateFixed size={20} />
              <h3>GPS Status</h3>
            </div>

            <button
              className={
                tracking
                  ? "secondary-button active"
                  : "secondary-button"
              }
              onClick={() =>
                setTracking(
                  (v) => !v
                )
              }
            >
              <Crosshair size={18} />

              {tracking
                ? "Stop GPS"
                : "Start GPS"}
            </button>

            <p className="panel-message">
              {gpsError
                ? gpsError
                : livePosition
                ? `Accuracy ${Math.round(
                    livePosition.accuracy ||
                      0
                  )} m`
                : "Waiting for GPS"}
            </p>
          </section>
        )}

        {/* METRICS */}

        <div className="metric-grid">
          <div>
            <Ambulance size={18} />

            <strong>
              {meters(
                routeData.responder_cost
              )}
            </strong>

            <span>Responder</span>
          </div>

          <div>
            <Hospital size={18} />

            <strong>
              {meters(
                routeData.hospital_cost
              )}
            </strong>

            <span>Hospital</span>
          </div>

          <div>
            <Navigation size={18} />

            <strong>
              {meters(totalDistance)}
            </strong>

            <span>Total</span>
          </div>

          <div>
            <Route size={18} />

            <strong>
              {fullPath.length}
            </strong>

            <span>Path Points</span>
          </div>
        </div>

        {/* PLAYBACK */}

        <section className="playback-card">
          <div className="section-title">
            <Radar size={20} />

            <h3>
              Vehicle Movement
            </h3>
          </div>

          <div className="movement-row">
            <button
              className="icon-button"
              onClick={() =>
                setPlaying(
                  (v) => !v
                )
              }
            >
              {playing ? (
                <Pause size={18} />
              ) : (
                <Play size={18} />
              )}
            </button>

            <div className="movement-copy">
              <strong>
                Ambulance Tracking
              </strong>

              <span>
                Point{" "}
                {Math.min(
                  playbackIndex + 1,
                  fullPath.length
                )}{" "}
                / {fullPath.length}
              </span>
            </div>
          </div>

          <label className="range-label">
            Playback Speed

            <input
              type="range"
              min="300"
              max="1800"
              step="50"
              value={speed}
              onChange={(e) =>
                setSpeed(
                  Number(
                    e.target.value
                  )
                )
              }
            />
          </label>

          <label className="switch-row">
            <input
              type="checkbox"
              checked={
                followVehicle
              }
              onChange={(e) =>
                setFollowVehicle(
                  e.target.checked
                )
              }
            />

            Follow Vehicle
          </label>
        </section>

        {/* RESPONSE */}

        <div className="response-card">
          <div>
            <span>Algorithm</span>

            <strong>
              {routeData.algorithm}
            </strong>
          </div>

          <p>{message}</p>
        </div>
      </aside>
    </main>
  );
}

createRoot(
  document.getElementById("root")
).render(<App />);