NDOH Control Registration API
=============================

The Registration REST-based API allows for sending registrations to the system
to be processed and potentially create subscriptions to stage-based messaging.

Connection & Authentication
----------------------------

You'll be given a URL base and security token depending on the deployment
you are connecting to.

Authentication is via HTTP Headers. The `Authorization` header should be
`Token InsertSecurityTokenHere`.

The `Content-Type` header should be `application/json`.


Registration fields
----------------------------
The patient registration endpoint to `POST` to is: `/api/v2/registrations/`

The data provided should be:

1. `hcw_msisdn`: The cellphone in international format. E.g. `+27845111111` of the healthcare worker making the registration or `null` if self
2. `mom_msisdn`: The cellphone in international format of the mother in international format.
3. `mom_id_type`: Identification method from `sa_id`, `passport`, `null`
4. `mom_passport_origin`: passport origin if passport
5. `mom_lang`: from codes listed in Language Options
6. `mom_edd`: in `YYYY-MM-DD` format
7. `mom_id_no`: the identification data for SA ID or international passport
8. `mom_dob`: in `YYYY-MM-DD` format
9. `clinic_code`: integer, should be valid SA clinic code, or `null`
10. `authority`: from `clinic`, `chw`, `personal`

Passport Options
----------------
`mom_passport_origin` can be one of the following:

  * `zw`: `Zimbabwe`
  * `mz`: `Mozambique`
  * `mw`: `Malawi`
  * `ng`: `Nigeria`
  * `cd`: `DRC`
  * `so`: `Somalia`
  * `other`: `Other`

Language Options
----------------
`mom_lang` can be one of the following:

 * `zu`: `isiZulu`
 * `xh`: `isiXhosa`
 * `af`: `Afrikaans`
 * `en`: `English`
 * `nso`: `Sesotho sa Leboa`
 * `tn`: `Setswana`
 * `st`: `Sesotho`
 * `ts`: `Xitsonga`
 * `ss`: `siSwati`
 * `ve`: `Tshivenda`
 * `nr`: `isiNdebele`



Example Payloads
----------------------------------

Clinic Health Care Worker-led on mothers device:

.. code-block:: javascript

  {
        "hcw_msisdn": null,
        "mom_msisdn": "+27001",
        "mom_id_type": "sa_id",
        "mom_passport_origin": null,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "8009151234001",
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    }

Clinic Health Care Worker-led on HCW device:

.. code-block:: javascript

    {
        "hcw_msisdn": "+27820010001",
        "mom_msisdn": "+27001",
        "mom_id_type": "passport",
        "mom_passport_origin": "zw",
        "mom_lang": "af",
        "mom_edd": "2015-09-01",
        "mom_id_no": "5551111",
        "mom_dob": null,
        "clinic_code": "12345",
        "authority": "clinic"
    }

Community Health Care Worker-led on mothers device:

.. code-block:: javascript

    {
        "hcw_msisdn": null,
        "mom_msisdn": "+27002",
        "mom_id_type": "none",
        "mom_passport_origin": null,
        "mom_lang": "xh",
        "mom_edd": null,
        "mom_id_no": null,
        "mom_dob": "1980-10-15",
        "clinic_code": null,
        "authority": "chw"
    }

Community Health Care Worker-led on HCW device:

.. code-block:: javascript

    {
        "hcw_msisdn": "+27820020002",
        "mom_msisdn": "+27002",
        "mom_id_type": "sa_id",
        "mom_passport_origin": null,
        "mom_lang": "zu",
        "mom_edd": null,
        "mom_id_no": "8011151234001",
        "mom_dob": "1980-11-15",
        "clinic_code": null,
        "authority": "chw"
    }

Detailed self-registration:

.. code-block:: javascript


    {
        "hcw_msisdn": null,
        "mom_msisdn": "+27003",
        "mom_id_type": "passport",
        "mom_passport_origin": "mz",
        "mom_lang": "st",
        "mom_edd": null,
        "mom_id_no": "5552222",
        "mom_dob": null,
        "clinic_code": null,
        "authority": "personal"
    }

Minimal self-registration:

.. code-block:: javascript

    {
        "hcw_msisdn": null,
        "mom_msisdn": "+27004",
        "mom_id_type": "none",
        "mom_passport_origin": null,
        "mom_lang": "ss",
        "mom_edd": null,
        "mom_id_no": null,
        "mom_dob": null,
        "clinic_code": null,
        "authority": "personal"
    }
