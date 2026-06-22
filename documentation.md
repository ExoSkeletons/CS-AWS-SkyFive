# SkyFive API & Microservices Documentation

This document serves as the technical reference for the SkyFive serverless application. It details the data layer schemas, Lambda microservices, API Gateway endpoints, and expected parameters.

---

## Data Layer Reference

### DynamoDB Tables

#### `sat-tle-cache`

Caches Two-Line Element (TLE) data and metadata for satellites to prevent redundant external API calls.

* **Partition Key (HASH):** `norad_id` (Number) - The unique NORAD catalog ID of the satellite.
* **TTL Attribute:** `expires` (Number) - Unix timestamp for automatic record deletion.

#### `sat-travellers`

Maps which users are currently "riding" or tracking which satellites.

* **Partition Key (HASH):** `norad_id` (Number)
* **Sort Key (RANGE):** `user_id` (String) - The Cognito sub/UUID of the user.
* **Global Secondary Index (`ByUsers`):**
* Partition Key: `user_id` (String)
* Sort Key: `norad_id` (Number)
* *Purpose:* Allows efficient querying of all satellites a specific user is tracking.


* **TTL Attribute:** `ttl` (Number) - Unix timestamp to auto-expire stale riders.

#### `user-highfives`

Immutable ledger of all high-five interactions between users.

* **Partition Key (HASH):** `timestamp` (Number) - Unix timestamp of the interaction.
* **Sort Key (RANGE):** `giver_id` (String) - The Cognito UUID of the user initiating the high-five.
* **Global Secondary Index (`GiverIndex`):** HASH `giver_id`, RANGE `timestamp`.
* **Global Secondary Index (`ReceiverIndex`):** HASH `receiver_id`, RANGE `timestamp`.
* **TTL Attribute:** `expiration` (Number)





# SkyFive API & Microservices Documentation

This document serves as the technical reference for the SkyFive serverless application. It details the data layer schemas, User Role-Based Access Control (RBAC) rules, Lambda microservices, API Gateway endpoints, and expected parameters.

---

## Cognito User Tiers & Authorization Rules

The application enforces features and access control limits based on three distinct user tiers resolved via AWS Cognito ID tokens (`event['requestContext']['authorizer']['claims']['cognito:groups']`).

| Tier / Role      | Cognito User Group | Route Access Controls                                                                                     | High-Five `hitsTtl` Feature Limits                                                                                    |
|------------------|--------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| **Default User** | *None* (No Group)  | Can only add, modify, or remove **themselves** from a satellite track.                                    | **1** — Evicted from the satellite tracking list immediately after receiving a single return high-five.               |
| **Paid User**    | `paid`             | Can only add, modify, or remove **themselves** from a satellite track.                                    | **3** (Configurable) — Can receive up to 3 returned high-fives before being evicted from the satellite tracking list. |
| **Admin User**   | `admin`            | Full administrative access. Authorized to remove **all users** or clear an entire satellite path context. | **99** — Effectively persistent tracking capabilities across orbital passes.                                          |

### Access Control Enforcement

* Any non-admin user (Default or Paid) attempting to hit administrative endpoints will be blocked at the gateway or code evaluation layer, returning a `403 Unauthorized` response.
* Self-service endpoints validate that the requested modifications target the matching Cognito `sub` claim parsed from the authorization payload.

---



## Admin Information

### Simple Notification Service (SNS)

#### `sat-events` Topic

* **Purpose:** Asynchronous event bus for system notifications. Currently configured to broadcast high-five events to subscribed administrators via email.
* **Publishers:** `LambdaHighfive`

---

## API & Microservices Reference

### 1. Satellite Discovery & Tracking

#### `LambdaNearby`

Scans and returns satellites currently located near the user's physical coordinates.

* **API Endpoint:** `GET /sat/nearby`
* **Authorization:** None (Public)
* **Query Parameters:**
* `latitude` *(Float, Required)*: User's physical latitude.
* `longitude` *(Float, Required)*: User's physical longitude.



#### `LambdaSatPathPredict`

Calculates and returns the projected orbital path of a specific satellite.

* **API Endpoint:** `GET /sat/{norad_id}/path`
* **Authorization:** Cognito
* **Path Parameters:**
* `norad_id` *(Integer, Required)*: The NORAD ID of the target satellite.



#### `LambdaSatInfo`

Retrieves or invalidates cached meta-information and TLE data for a satellite.

* **API Endpoints:**
* `GET /sat/{norad_id}` - Fetch satellite info.
* `DELETE /sat/{norad_id}` - Clear cached info.


* **Authorization:** Cognito
* **Path Parameters:**
* `norad_id` *(Integer, Required)*



---

### 2. User & Rider Management

#### `LambdaUserGetTrackedSats`

Retrieves a list of satellites being tracked by a specific user or the currently authenticated user.

* **API Endpoints:**
* `GET /my/sats` - Resolves `user_id` from the Cognito Authorization JWT.
* `GET /u/{user_id}` - Fetches sats for a specific target user.


* **Authorization:** Cognito
* **Path Parameters (for `/u/{user_id}`):**
* `user_id` *(String, Required)*



#### `LambdaGetSatTravellers`

Retrieves a list of all users currently tracking/riding a specific satellite.

* **API Endpoint:** `GET /sat/{norad_id}/travellers`
* **Authorization:** Cognito
* **Path Parameters:**
* `norad_id` *(Integer, Required)*



#### `LambdaUpdateSatRider`

Adds, modifies, or removes a user's tracking status on a specific satellite.

* **API Endpoints:**
* `POST /sat/{norad_id}/travellers` - Add self to satellite.
* `PUT /sat/{norad_id}/travellers` - Update tracking metrics/TTL.
* `DELETE /sat/{norad_id}/travellers` - Remove self from satellite.


* **Authorization:** Cognito
* **Path Parameters:**
* `norad_id` *(Integer, Required)*
* **Access Control Validation:** Non-admin callers can only manipulate rows matching their own authenticated `user_id`.
* **Feature Logic Enforcement:**
* When a user creates a record (`POST`), the code evaluates their role to assign the initial `hitsTtl` value: **1** for Default, **3** for Paid, or **99** for Admin.




---

### 3. Interactions (High-Fives)

#### `LambdaHighfive`

Initiates a high-five interaction targeting other users on the same satellite. Validates request payload against the strict API Gateway `HighFiveInfo` JSON Schema.

* **API Endpoint:** `POST /sat/{norad_id}/highfive`
* **Authorization:** Cognito
* **Path Parameters:**
* `norad_id` *(Integer, Required)*


* **Request Body Schema (`application/json`):**
```json
{
  "from": {
    "username": "string (min length: 1)",
    "location": {
      "latitude": 0.0,
      "longitude": 0.0,
      "altitude": 0.0
    }
  }
}

```


* **Effects:**
* Calculates targets via `sat-travellers`.
* Appends interaction records to `user-highfives`, caching user inforamtions such as ```username``` and ```location``` is placed in the ```giver_profile``` attribute.
* Publishes the interaction event payload to the `sat-events` SNS Topic.



#### `LambdaGetHighfives`

Retrieves chronological lists of high-fives the authenticated user has either initiated or received.

* **API Endpoints:**
* `GET /my/given` - Fetches interactions where the user is the `giver_id`.
* `GET /my/received` - Fetches interactions where the user is the `receiver_id`.
* User inforamtions such as ```username``` and ```location``` is pulled from the ```giver_profile``` attribute.


* **Authorization:** Cognito
* **Execution Profile:** Uses the `GiverIndex` and `ReceiverIndex` DynamoDB Global Secondary Indexes to retrieve interactions sorted by timestamp descending.